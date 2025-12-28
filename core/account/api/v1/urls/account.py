from django.urls import path
from .. import views

# JWT utilities from Django REST Framework SimpleJWT
from rest_framework_simplejwt.views import (
    TokenRefreshView,
    TokenVerifyView,
)

urlpatterns = [

    # -----------------------------
    # User Registration
    # -----------------------------
    # Handles initial user signup (typically creates an inactive user)
    path(
        "registration/",
        views.RegistrationAPIView.as_view(),
        name="registration",
    ),

    # -----------------------------
    # Account Activation
    # -----------------------------
    # Confirms account activation using a unique activation token
    path(
        "activation/confirm/<str:token>/",
        views.ActivationAPIView.as_view(),
        name="activation",
    ),

    # Resends activation token (used when token expires or is lost)
    path(
        "activation/resend/",
        views.ActivationResendAPIView.as_view(),
        name="activation-resend",
    ),

    # -----------------------------
    # JWT Authentication
    # -----------------------------
    # Issues access and refresh tokens after successful login
    path(
        "jwt/create/",
        views.CustomTokenObtainPairView.as_view(),
        name="jwt_create",
    ),

    # Generates a new access token using a valid refresh token
    path(
        "jwt/refresh/",
        TokenRefreshView.as_view(),
        name="jwt_refresh",
    ),

    # Verifies the validity of an access or refresh token
    path(
        "jwt/verify/",
        TokenVerifyView.as_view(),
        name="jwt_verify",
    ),

    # -----------------------------
    # JWT Logout
    # -----------------------------
    # Invalidates token (usually via blacklist or deletion logic)
    path(
        "logout/",
        views.CustomDiscardAuthToken.as_view(),
        name="jwt_logout",
    ),

    # -----------------------------
    # Password Management
    # -----------------------------
    # Allows authenticated users to change their password
    path(
        "change-password/",
        views.ChangePasswordAPIView.as_view(),
        name="change_password",
    ),
]
