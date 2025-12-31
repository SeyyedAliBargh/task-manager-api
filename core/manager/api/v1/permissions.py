from rest_framework.permissions import BasePermission
from manager.models import Project, ProjectMember
from django.db.models import Q

class IsOwnerOrAdminMember(BasePermission):
    """
    Custom permission class to check if the user is either:
    - The project owner, OR
    - An admin/owner member of the project.

    Rules:
    - For GET requests: user must be either the owner or a member of the project.
    - For other requests (update/delete): user must be the owner or have role OWNER/ADMIN.
    """

    def has_object_permission(self, request, view, obj):
        # Get the current user's profile
        profile = request.user.profile

        # For GET requests: allow if user is project owner or a member
        if request.method == "get":
            return obj.members.filter(user=profile).exists() or obj.owner == profile

        # Allow if user is the project owner
        if obj.owner == profile:
            return True

        # Allow if user is a member with OWNER or ADMIN role
        return obj.members.filter(
            user=profile,
            role__in=[ProjectMember.Role.OWNER, ProjectMember.Role.ADMIN]
        ).exists()