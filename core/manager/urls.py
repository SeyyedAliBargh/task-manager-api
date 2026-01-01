from django.urls import path, include


app_name = "manager"

urlpatterns = [
    path('manager/api/v1/', include('manager.api.v1.urls', namespace='manager_api'))
]