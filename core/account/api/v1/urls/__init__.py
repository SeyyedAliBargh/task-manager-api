from django.urls import path, include

app_name = "api-v1"

urlpatterns = [
    path("", include("account.api.v1.urls.account")),
    path("profile/", include("account.api.v1.urls.profile")),
]
