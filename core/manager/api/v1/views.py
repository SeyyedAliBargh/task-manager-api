from rest_framework import generics, status
from manager.api.v1.serializer import ProjectsSerializer, CreateProjectSerializer, ProjectInvitationSerializer
from ...models import Project, ProjectMember, ProjectInvitation
from account.models import Profile
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from manager.api.v1.paginations import DefaultPagination
from django.db.models import Q, Prefetch            
from .permissions import IsOwnerOrAdminMember
from django.shortcuts import get_object_or_404
from ...tasks import send_registration_email
from rest_framework_simplejwt.tokens import RefreshToken
import jwt
from django.conf import settings
from jwt import ExpiredSignatureError, InvalidSignatureError


class PublicProjectsAPIView(generics.ListAPIView):
    """
    API view that provides a paginated list of all public projects.

    - Uses `ProjectsSerializer` to serialize project data.
    - Accessible to any user (no authentication required).
    - Orders projects by creation date in descending order.
    - Pagination is handled by `DefaultPagination`.
    """
    queryset = Project.objects.filter(status=Project.Visibility.PUBLIC).order_by('-created')
    permission_classes = [AllowAny]
    pagination_class = DefaultPagination
    serializer_class = ProjectsSerializer


class CreateProjectAPIView(generics.CreateAPIView):
    """
    API view that allows authenticated users to create a new project.

    - Requires user authentication (`IsAuthenticated`).
    - Uses `CreateProjectSerializer` to validate and save project data.
    - Operates on the full set of `Project` objects.
    """
    permission_classes = [IsAuthenticated]
    serializer_class = CreateProjectSerializer
    queryset = Project.objects.all()


class MyProjectsAPIView(generics.ListAPIView):
    """
    API view that returns a paginated list of projects related to the authenticated user.

    - Requires user authentication (`IsAuthenticated`).
    - Uses `ProjectsSerializer` to serialize project data.
    - Pagination is handled by `DefaultPagination`.
    - Includes projects where:
        * The user is the owner, OR
        * The user is a member with roles: OWNER, ADMIN, or MEMBER.
    - Prefetches membership information for the current user, excluding the VIEWER role.
    - Results are distinct and ordered by creation date in descending order.
    """

    permission_classes = [IsAuthenticated]
    pagination_class = DefaultPagination
    serializer_class = ProjectsSerializer

    def get_queryset(self):
        """
        Returns the queryset of projects associated with the authenticated user.

        - Filters projects by ownership or membership roles.
        - Prefetches membership details for optimization.
        - Ensures distinct results ordered by creation date.
        """
        profile = self.request.user.profile
        projects = Project.objects.filter(
            Q(owner=profile) |
            Q(members__user=profile,
              members__role__in=[
                  ProjectMember.Role.OWNER,
                  ProjectMember.Role.ADMIN,
                  ProjectMember.Role.MEMBER,
              ]),
        ).prefetch_related(
            Prefetch(
                'members',
                queryset=ProjectMember.objects.filter(user=profile)
                .exclude(role=ProjectMember.Role.VIEWER),
                to_attr='current_user_membership'
            )
        ).distinct().order_by('-created')

        return projects


class PublicDetailProjectAPIView(generics.RetrieveAPIView):
    """
    API view that retrieves detailed information about a single project.

    - Accessible to any user (no authentication required).
    - Uses `ProjectsSerializer` to serialize project data.
    - Operates on the full set of `Project` objects.
    """
    serializer_class = ProjectsSerializer
    permission_classes = [AllowAny]
    queryset = Project.objects.all()


class MyDetailProjectAPIView(generics.RetrieveUpdateDestroyAPIView):
    """
    API view that allows authenticated users to retrieve, update, or delete a specific project.

    - Requires authentication (`IsAuthenticated`).
    - Additional permission check: user must be the owner or an admin member (`IsOwnerOrAdminMember`).
    - Uses `ProjectsSerializer` to handle serialization.
    - Operates on the full set of `Project` objects.
    """
    serializer_class = ProjectsSerializer
    permission_classes = [IsAuthenticated, IsOwnerOrAdminMember]
    queryset = Project.objects.all()


class ProjectInvitationAPIView(generics.GenericAPIView):
    """
    API view that handles sending project invitations.

    - Requires authentication and owner/admin permissions.
    - Uses `ProjectInvitationSerializer` to validate and save invitation data.
    - Operates on the full set of `ProjectInvitation` objects.
    - Provides a `POST` method to send invitations via email.
    """

    serializer_class = ProjectInvitationSerializer
    permission_classes = [IsAuthenticated, IsOwnerOrAdminMember]
    queryset = ProjectInvitation.objects.all()

    def post(self, request, *args, **kwargs):
        """
        Handles the creation and sending of a project invitation.

        - Validates the provided email.
        - Creates an invitation record.
        - Generates a token for the invited user.
        - Sends a registration email asynchronously.
        - Returns success or error response depending on the outcome.
        """
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            email = serializer.validated_data['email']
            profile = get_object_or_404(Profile, user__email=email)
            full_name = profile.get_full_name()

            try:
                # Save invitation object
                invitation = serializer.save()

                # Prepare response data
                data = {
                    "detail": "Your invitation letter has been sent.",
                    "email": email,
                    "full_name": full_name,
                }

                # Generate activation token for invited user
                token = self.get_token_for_user(profile.user, invitation)

                # Send invitation email asynchronously
                send_registration_email.apply_async(kwargs={
                    "token": token,
                    "full_name": full_name,
                    "email": email,
                })

                return Response(data=data, status=status.HTTP_201_CREATED)

            except Exception as e:
                # Rollback invitation if error occurs
                ProjectInvitation.objects.get(invitee=profile).delete()
                print(f"error: {str(e)}")

                return Response(
                    {"detail": "An error occurred, please try again later and call to admins"},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                )

        # Return validation errors
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def get_token_for_user(self, user, invitation):
        """
        Generates an access token for account activation.

        - Token includes invitation ID, role, and project ID.
        - Uses `RefreshToken` to generate the access token.
        """
        refresh = RefreshToken.for_user(user)
        refresh['invitation_id'] = str(invitation.id)
        refresh['role'] = invitation.role
        refresh['project_id'] = str(invitation.project.id)
        return str(refresh.access_token)


class AcceptInvitationAPIView(generics.GenericAPIView):
    """
    API view that allows authenticated users to accept a project invitation.

    - Requires authentication (`IsAuthenticated`).
    - Accepts a token to validate the invitation.
    - Creates a `ProjectMember` record for the user with the specified role.
    - Updates the invitation status to `ACCEPTED`.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request, token, *args, **kwargs):
        """
        Handles the acceptance of a project invitation.

        - Decodes the provided JWT token.
        - Validates invitation existence and status.
        - Creates a new project member with the given role.
        - Updates invitation status to accepted.
        - Returns success or error response depending on the outcome.
        """
        try:
            # Decode JWT token to extract invitation details
            pyload = jwt.decode(
                jwt=token,
                key=settings.SECRET_KEY,
                algorithms=["HS256"],
            )
            user_id = pyload["user_id"]
            project_id = pyload["project_id"]
            role = pyload["role"]
            invitation_id = pyload["invitation_id"]
        except ExpiredSignatureError:
            # Token expired
            return Response(
                {"detail": "Token Expired"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        except InvalidSignatureError:
            # Token invalid
            return Response(
                {"detail": "Invalid Token"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            # Fetch invitation from the database
            invitation = ProjectInvitation.objects.get(
                id=invitation_id,
                status=ProjectInvitation.Status.PENDING
            )

            # Fetch project and profile
            project = get_object_or_404(Project, id=project_id)
            profile = get_object_or_404(Profile, pk=user_id)

            # Create ProjectMember with specified role
            member = ProjectMember.objects.create(
                project=project,
                user=profile,
                role=role
            )

            # Update invitation status to ACCEPTED
            invitation.status = ProjectInvitation.Status.ACCEPTED
            invitation.save()

            return Response({
                "detail": "Invitation accepted successfully",
                "project": project.name,
                "role": role,
                "member_id": str(member.id)
            }, status=status.HTTP_200_OK)

        except ProjectInvitation.DoesNotExist:
            # Invitation not found or already processed
            return Response(
                {"detail": "Invitation not found or already processed"},
                status=status.HTTP_404_NOT_FOUND,
            )
        except Exception as e:
            # General error handling
            print(f"Error accepting invitation: {str(e)}")
            return Response(
                {"detail": "An error occurred while processing the invitation"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class RejectInvitationAPIView(generics.GenericAPIView):
    permission_classes = [IsAuthenticated]
    def get(self, request, token, *args, **kwargs):
        try:
            pyload = jwt.decode(
                jwt=token,
                key=settings.SECRET_KEY,
                algorithms=["HS256"],
            )
            user_id = pyload["user_id"]
            project_id = pyload["project_id"]
            role = pyload["role"]
            invitation_id = pyload["invitation_id"]
        except ExpiredSignatureError:
            # Token expired
            return Response(
                {"detail": "Token Expired"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        except InvalidSignatureError:
            # Token invalid
            return Response(
                {"detail": "Invalid Token"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            invitation = ProjectInvitation.objects.get(pk=invitation_id)
            invitation.status = ProjectInvitation.Status.REVOKED
            return Response({
                "detail": "Invitation revoked successfully",
            })

        except ProjectInvitation.DoesNotExist:
            return Response({"detail": "Invitation not found or already processed"},)

        except Exception as e:
            print(f"Error rejecting invitation: {str(e)}")
            return Response(
                {"detail": "An error occurred while processing the invitation"},
            )
