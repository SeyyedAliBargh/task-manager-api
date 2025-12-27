from django.urls import path, include


app_name = "manager"

urlpatterns = [
    path('manager/', include('manager.api.v1.urls', namespace='manager_api'))
]