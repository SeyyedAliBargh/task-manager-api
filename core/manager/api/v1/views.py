from rest_framework import generics
from manager.api.v1.serializer import SerializerProjects
from ...models import Project, ProjectMember
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from manager.api.v1.paginations import DefaultPagination
from django.db.models import Q, Prefetch              
class PublicProjectsAPIView(generics.ListAPIView):
    queryset = Project.objects.filter(status=Project.Visibility.PUBLIC).order_by('-created')
    permission_classes = [AllowAny]
    pagination_class = DefaultPagination
    serializer_class = SerializerProjects
    

# class CreateProject(generics.GenericAPIView):
#     serializer_class = SerializerProjects
#     permission_classes = [IsAuthenticated]
#     def post(self, request, *args, **kwargs):
#         serializer = self.get_serializer(data = request.data)
        


class MyProjectsAPIView(generics.ListAPIView):
    permission_classes = [IsAuthenticated]
    pagination_class = DefaultPagination
    serializer_class = SerializerProjects

    def get_queryset(self):
        profile = self.request.user.profile
        projects = Project.objects.filter(
            Q(owner = profile)|
            Q(members__user = profile),
            members__role__in=[
                ProjectMember.Role.OWNER,
                ProjectMember.Role.ADMIN,
                ProjectMember.Role.MEMBER,
            ]
        ).prefetch_related(
            Prefetch(
                'members',
                queryset = ProjectMember.objects.filter(user = profile)
                .exclude(role = ProjectMember.Role.VIEWER),
                to_attr = 'current_user_membership'
            )
        ).distinct()

        return projects
    
class DetailProjectAPIView(generics.RetrieveAPIView):
    serializer_class = SerializerProjects
    permission_classes = [IsAuthenticated]
    queryset = Project.objects.all()
