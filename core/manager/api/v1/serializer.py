from rest_framework import serializers
from manager.models import Project, ProjectMember, Task, ProjectInvitation
from account.models import Profile
from django.shortcuts import get_object_or_404
from django.utils import timezone

class TaskSerializer(serializers.ModelSerializer):
    """
    Serializer for the Task model.

    - Provides serialization for task-related fields.
    - Includes metadata such as creation and update timestamps.
    """
    email = serializers.EmailField(write_only=True)
    class Meta:
        model = Task
        fields = ['project' ,'title', 'description', 'email', 'due_date', 'priority','status', 'created_by', 'created', 'updated']
        read_only_fields = ['status', 'created_by', 'created', 'updated', 'project']

    def validate(self, attrs):
        email = attrs.get('email')
        if not ProjectMember.objects.filter(profile__user__email=email).exists():
            raise serializers.ValidationError('This user is not a member of the project.')
        if not Profile.objects.filter(user__email=email).exists():
            raise serializers.ValidationError('This user does not exist')
        # بررسی زمان due_date
        due_date = attrs.get('due_date')
        # اگر آبجکت جدید باشه، created هنوز ساخته نشده → از زمان فعلی استفاده کن
        created_time = getattr(self.instance, 'created', timezone.now())

        if due_date and due_date < created_time:
            raise serializers.ValidationError({
                'due_date': 'زمان پایان نمی‌تواند قبل از زمان ایجاد باشد.'
            })

        return attrs

    def create(self, validated_data):
        request = self.context.get('request')
        validated_data['created_by'] = request.user
        profile = Profile.objects.get(email=validated_data['email'])
        project_id = request.parser_context["kwargs"]["pk"]
        project = get_object_or_404(Project, pk=project_id)
        # عضو پروژه را پیدا کن
        project_member = ProjectMember.objects.get(
            project=project,
            user=profile
        )

        task = Task.objects.create(
            title= validated_data['title'],
            description= validated_data['description'],
            assignee=project_member,
            project=project,
            due_date=validated_data['due_date'],
            created_by=validated_data['created_by'],
            status=Task.Status.TODO,
            priority=validated_data['priority'],
        )

        return task



class ProjectsSerializer(serializers.ModelSerializer):
    """
    Serializer for the Project model.

    - Includes project owner information via `get_owner`.
    - Serializes related tasks using `TaskSerializer`.
    - Provides additional fields: `min_description`, `absolute_url`, and `role`.
    - Customizes representation depending on whether a project detail view or list view is requested.
    """

    # Custom field to return project owner's email
    owner = serializers.SerializerMethodField(method_name="get_owner")

    # Nested serializer for related tasks
    tasks = TaskSerializer(many=True, read_only=True)

    # Read-only field for shortened description
    min_description = serializers.ReadOnlyField()

    # Custom field to return absolute URL of the project
    absolute_url = serializers.SerializerMethodField(method_name="get_absolute_url")

    # Custom field to return the role of the current user in the project
    role = serializers.SerializerMethodField(method_name="get_role")

    class Meta:
        model = Project
        fields = (
            'id', 'owner', 'name', 'role', 'description',
            'min_description', 'created', 'updated',
            'status', 'absolute_url', 'tasks'
        )
        read_only_fields = ["id", "owner", "created", "updated"]

    def to_representation(self, instance):
        """
        Customize the serialized representation of the project.

        - If a specific project (`pk`) is requested:
            * Remove `absolute_url` and `min_description`.
        - If listing projects:
            * Remove `description` and `tasks` for brevity.
        """
        request = self.context.get('request')
        rep = super().to_representation(instance)

        if request.parser_context.get("kwargs").get("pk"):
            # Detail view: remove URL and min_description
            rep.pop("absolute_url")
            rep.pop("min_description")
        else:
            # List view: remove description and tasks
            rep.pop("description")
            rep.pop("tasks")

        return rep

    def get_owner(self, obj):
        """Return the email of the project owner."""
        return obj.owner.user.email

    def get_role(self, obj):
        """
        Return the role of the current user in the project.

        - If the user is the project owner → 'owner'.
        - If the user is a member → return their role.
        - Otherwise → None.
        """
        profile = self.context['request'].user.profile

        # If the person is the project owner
        if obj.owner_id == profile.id:
            return 'owner'

        # If the person is a member
        membership = getattr(obj, 'current_user_membership', None)
        if membership:
            return membership[0].role

        return None

    def get_absolute_url(self, obj):
        """Return the absolute URL for the project instance."""
        request = self.context.get("request")
        return request.build_absolute_uri(obj.pk)

    def create(self, validated_data):
        """
        Create a new project with the current user as the owner.
        """
        validated_data['owner'] = self.context['request'].user.profile
        return super().create(validated_data)


class CreateProjectSerializer(serializers.ModelSerializer):
    """
    Serializer for creating a new project.

    - Automatically assigns the current user as the project owner.
    - Creates a `ProjectMember` record with role 'owner'.
    """

    class Meta:
        model = Project
        fields = [
            'id', 'owner', 'name', 'description',
            'created', 'updated', 'status'
        ]
        read_only_fields = ["id", "owner", "created", "updated"]

    def create(self, validated_data):
        """
        Create a new project and assign the current user as owner.

        - Sets the owner field to the authenticated user's profile.
        - Creates a corresponding `ProjectMember` record with role 'owner'.
        """
        validated_data['owner'] = self.context.get('request').user.profile

        # Create project instance
        project = super().create(validated_data)

        # Create project membership for the owner
        ProjectMember.objects.create(
            project=project,
            role='owner',
            user=self.context.get('request').user.profile
        )

        return project


class ProjectInvitationSerializer(serializers.ModelSerializer):
    """
    Serializer for handling project invitations.

    - Accepts an email and role for the invited user.
    - Validates that the user exists, is not already a member,
      and does not have an active pending invitation.
    - Creates a new ProjectInvitation instance if validation passes.
    """

    # Email field is write-only (not returned in response)
    email = serializers.EmailField(write_only=True)

    class Meta:
        model = ProjectInvitation
        fields = ['email', 'role']

    def validate(self, attrs):
        """
        Validate invitation data before creation.

        - Ensure the provided email belongs to an existing user.
        - Ensure the user is not already a member of the project.
        - Ensure there is no active pending invitation for the user.
        """
        # Check if user with given email exists
        if not Profile.objects.filter(user__email=attrs['email']).exists():
            raise serializers.ValidationError({"detail": "No user with this email exists."})

        # Get project from request context
        request = self.context["request"]
        project_id = request.parser_context["kwargs"]["pk"]
        project = get_object_or_404(Project, pk=project_id)

        # Get invitee profile
        invitee = Profile.objects.get(user__email=attrs["email"])

        # Check if invitee is already a member of the project
        if ProjectMember.objects.filter(project=project, user=invitee).exists():
            raise serializers.ValidationError({"detail": "The user is a member of the project"})

        # Check if there is already a pending invitation for this user
        if ProjectInvitation.objects.filter(
                project=project,
                invitee=invitee,
                status=ProjectInvitation.Status.PENDING
        ).exists():
            raise serializers.ValidationError({"detail": "There is an active invitation for this user."})

        return attrs

    def create(self, validated_data):
        """
        Create a new project invitation.

        - Retrieves the project from request context.
        - Finds the invitee profile using the provided email.
        - Creates a ProjectInvitation with the specified role and inviter.
        """
        request = self.context["request"]

        # Get project from request context
        project = Project.objects.get(pk=request.parser_context["kwargs"]["pk"])

        # Get invitee profile from email
        invitee = Profile.objects.get(user__email=validated_data.pop("email"))

        # Create invitation record
        invitation = ProjectInvitation.objects.create(
            project=project,
            invitee=invitee,
            role=validated_data["role"],
            invited_by=request.user.profile
        )
        return invitation


