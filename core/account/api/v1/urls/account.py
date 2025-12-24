from django.urls import path, include
from .. import views


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
