from django.urls import path, include
from .. import views
from rest_framework.authtoken.views import ObtainAuthToken
from rest_framework_simplejwt.views import (

    TokenRefreshView,
    TokenVerifyView,
)


urlpatterns = [
    # registration
    path(
        "registration/",
        views.RegistrationAPIView.as_view(),
        name="registration",
    ),

    # verification
    path(
        "activation/confirm/<str:token>/",
        views.ActivationAPIView.as_view(),
        name="activation",
    ),
    path(
        "activation/resend/",
        views.ActivationResendAPIView.as_view(),
        name="activation-resend",

    ),
    path("jwt/create/", views.CustomTokenObtainPairView.as_view(), name="jwt_create"),
    path("jwt/refresh/", TokenRefreshView.as_view(), name="jwt_refresh"),
    path("jwt/verify/", TokenVerifyView.as_view(), name="jwt_verify"),
]
