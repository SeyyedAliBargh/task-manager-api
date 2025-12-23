from django.urls import path, include
from .. import views
from rest_framework.authtoken.views import ObtainAuthToken
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
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
]
