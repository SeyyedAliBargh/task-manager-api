import uuid
from django.db import models
from django.urls import reverse
from core.account.models import Profile


# =========================
# Project Model
# =========================
# Represents a project container that groups tasks and members together
class Project(models.Model):

    # Controls project visibility and accessibility
    class Visibility(models.TextChoices):
        PRIVATE = ("private", "Private")
        PUBLIC = ("public", "Public")
        CLOSED = ("closed", "Closed")

    # Use UUID as primary key for better security and scalability
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # Basic project information
    name = models.CharField(max_length=100)
    description = models.TextField()

    # Project owner (creator). Deleting owner deletes the project.
    owner = models.ForeignKey(
        Profile, on_delete=models.CASCADE, related_name="projects"
    )

    # Timestamps
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)

    # Project visibility status
    status = models.CharField(
        max_length=20, choices=Visibility.choices, default=Visibility.PRIVATE
    )

    def __str__(self):
        return f"{self.name} created by {self.owner.first_name}"

    # Canonical URL for project detail endpoint
    def get_absolute_url(self):
        return reverse("project-detail", kwargs={"pk": self.id})

    class Meta:
        # Default ordering for querysets
        ordering = ("created", "name")

        # Indexes for common query patterns
        indexing = [
            models.Index(fields=["created", "status"]),
            models.Index(fields=["name"]),
        ]


# =========================
# Task Model
# =========================
# Represents an actionable unit inside a project
class Task(models.Model):

    # Task workflow states
    class Status(models.TextChoices):
        TODO = ("todo", "To Do")
        IN_PROGRESS = ("in_progress", "In Progress")
        DONE = ("done", "Done")

    # Task priority levels
    class Priority(models.TextChoices):
        LOW = ("low", "Low")
        MEDIUM = ("medium", "Medium")
        HIGH = ("high", "High")

    # UUID primary key
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # Parent project
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="tasks")

    # Task content
    title = models.CharField(max_length=200)
    description = models.TextField()

    # Assigned user (optional)
    assignee = models.ForeignKey(
        Profile, on_delete=models.SET_NULL, related_name="assigned_tasks", null=True
    )

    # Task creator (optional, preserved even if user is deleted)
    created_by = models.ForeignKey(
        Profile, on_delete=models.SET_NULL, related_name="created_tasks", null=True
    )

    # Task state and importance
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.TODO
    )
    priority = models.CharField(
        max_length=20, choices=Priority.choices, default=Priority.MEDIUM
    )

    # Optional deadline
    due_date = models.DateTimeField(null=True, blank=True)

    # Audit timestamps
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)

    # Soft delete fields (task is hidden, not removed from DB)
    is_deleted = models.BooleanField(default=False)
    deleted_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        assignee = self.assignee.first_name if self.assignee else "Unassigned"
        return f"{self.title} assigned to ({assignee})"

    # Canonical URL for task detail endpoint
    def get_absolute_url(self):
        return reverse("task-detail", kwargs={"pk": self.id})

    class Meta:
        # Default ordering (upcoming tasks first)
        ordering = ("due_date", "priority", "created")

        # Optimized indexes for frequent filtering
        indexes = [
            models.Index(fields=["project", "status"]),
            models.Index(fields=["assignee", "status"]),
            models.Index(fields=["created", "status"]),
        ]

        # Prevent invalid due dates (must be >= creation time)
        constraints = [
            models.CheckConstraint(
                check=models.Q(due_date__gte=models.F("created")),
                name="due_date_after_created",
            )
        ]


# =========================
# Project Membership Model
# =========================
# Defines which users have access to a project and with what role
class ProjectMember(models.Model):

    # Role-based access control
    class Role(models.TextChoices):
        OWNER = ("owner", "Owner")
        ADMIN = ("admin", "Admin")
        MEMBER = ("member", "Member")
        VIEWER = ("viewer", "Viewer")

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # Related project
    project = models.ForeignKey(
        Project, on_delete=models.CASCADE, related_name="members"
    )

    # User with access to the project
    user = models.ForeignKey(
        Profile, on_delete=models.CASCADE, related_name="project_memberships"
    )

    # Access role inside the project
    role = models.CharField(max_length=20, choices=Role.choices, default=Role.MEMBER)

    # Membership creation timestamp
    joined_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        # Ensure a user can only have one role per project
        unique_together = ("project", "user")

        indexes = [
            models.Index(fields=["project", "user"]),
            models.Index(fields=["user"]),
        ]

    def __str__(self):
        return f"{self.user} in {self.project} as {self.role}"


# =========================
# Project Invitation Model
# =========================
# Handles access requests sent to existing users
class ProjectInvitation(models.Model):

    # Invitation lifecycle states
    class Status(models.TextChoices):
        PENDING = ("pending", "Pending")
        ACCEPTED = ("accepted", "Accepted")
        REVOKED = ("revoked", "Revoked")
        EXPIRED = ("expired", "Expired")

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # Target project
    project = models.ForeignKey(
        Project, on_delete=models.CASCADE, related_name="invitations"
    )

    # User being invited (must exist in system)
    invitee = models.ForeignKey(
        Profile, on_delete=models.CASCADE, related_name="project_invitations"
    )

    # Role that will be assigned upon acceptance
    role = models.CharField(
        max_length=20,
        choices=ProjectMember.Role.choices,
        default=ProjectMember.Role.MEMBER,
    )

    # User who sent the invitation
    invited_by = models.ForeignKey(
        Profile, on_delete=models.CASCADE, related_name="sent_invitations"
    )

    # Invitation state
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.PENDING
    )

    # Creation timestamp
    created = models.DateTimeField(auto_now_add=True)

    class Meta:
        # Prevent duplicate invitations for same user & project
        unique_together = ("project", "invitee")

        indexes = [
            models.Index(fields=["invitee", "status"]),
            models.Index(fields=["project"]),
            models.Index(fields=["created"]),
        ]

    def __str__(self):
        return f"{self.invitee} invited to {self.project}"
