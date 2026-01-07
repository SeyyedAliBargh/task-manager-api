from django.urls import path
from . import views

app_name = "manager_api"

urlpatterns = [
    path('projects/', views.PublicProjectsAPIView.as_view(), name = 'public_projects'),
    path('projects/my/', views.MyProjectsAPIView.as_view(), name = 'my_projects'),
    path('projects/<str:pk>/', views.PublicDetailProjectAPIView.as_view(), name = 'detail_projects'),
    path('projects/my/<str:pk>/', views.MyDetailProjectAPIView.as_view(), name = 'detail_projects'),
    path('create/project/', views.CreateProjectAPIView.as_view(), name = 'create_project'),
    path('projects/my/<str:pk>/invite/', views.ProjectInvitationAPIView.as_view(), name = 'invition_user'),
    path('invition/accept/confirm/<str:token>/', views.AcceptInvitationAPIView.as_view(), name='invition_user'),
    path('invition/reject/confirm/<str:token>/', views.RejectInvitationAPIView.as_view(), name='invition_user'),
    path('projects/my/<str:pk>/create-task/', views.CreateTaskAPIView.as_view(), name='create_task'),
]