from django.urls import path
from . import views

app_name = "manager_api"

urlpatterns = [
    path('projects/', views.PublicProjectsAPIView.as_view(), name = 'public_projects'),
    path('projects/my/', views.MyProjectsAPIView.as_view(), name = 'my_projects'),
    path('projects/<str:pk>/', views.DetailProjectAPIView.as_view(), name = 'detail_projects'),


]