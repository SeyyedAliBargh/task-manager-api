from rest_framework import generics
from manager.api.v1.serializer import SerializerProjects
from ...models import Project
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from manager.api.v1.paginations import DefaultPagination

              
class PublicProjectsAPIView(generics.ListAPIView):
    queryset = Project.objects.filter(status=Project.Visibility.PUBLIC).order_by('-created')
    permission_classes = [AllowAny]
    pagination_class = DefaultPagination
    serializer_class = SerializerProjects
    

class MyProjectsAPIView(generics.ListAPIView):
    permission_classes = [IsAuthenticated]
    pagination_class = DefaultPagination
    serializer_class = SerializerProjects

    def get_queryset(self):
        return Project.objects.filter(
            owner=self.request.user.profile
        ).distinct()
    
class DetailProjectAPIView(generics.RetrieveAPIView):
    serializer_class = SerializerProjects
    permission_classes = [IsAuthenticated]
    queryset = Project.objects.all()
