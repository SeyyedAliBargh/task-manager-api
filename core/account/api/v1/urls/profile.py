from django.urls import path
from ..views import ProfileRetrieveUpdateAPIView
urlpatterns = [
    path("", ProfileRetrieveUpdateAPIView.as_view(), name="profile"),
]