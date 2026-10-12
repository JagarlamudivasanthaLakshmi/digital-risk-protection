from django.urls import path

from .views import RegistrationAPIView

urlpatterns = [path("api/register/", RegistrationAPIView.as_view(), name="api-register")]
