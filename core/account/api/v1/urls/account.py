from django.urls import path, include
from .. import views
from rest_framework_simplejwt.views import TokenRefreshView, TokenVerifyView
urlpatterns = [
    path("register/", views.RegisterUserAPIView.as_view(), name="register"),
    path("jwt/create/", views.CustomTokenObtainPairView.as_view(), name="jwt_create"),
    path("jwt/refresh/", TokenRefreshView.as_view(), name="jwt_refresh"),
    path("jwt/verify/", TokenVerifyView.as_view(), name="jwt_verify"),
]
