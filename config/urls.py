from django.contrib import admin
from django.contrib.auth.views import LoginView
from django.urls import include, path
from django.conf import settings
from django.conf.urls.static import static
from django.views.generic import TemplateView

from accounts.views import RegisterView
from dashboard.views import DashboardView

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", TemplateView.as_view(template_name="home.html"), name="home"),
    path("accounts/login/", LoginView.as_view(template_name="login.html"), name="login"),
    path("accounts/", include("django.contrib.auth.urls")),
    path("accounts/", include("accounts.urls")),
    path("accounts/register/", RegisterView.as_view(), name="register"),
    path("brands/", include("brands.urls")),
    path("monitoring/", include("monitoring.urls")),
    path("detection/", include("detection.urls")),
    path("alerts/", include("alerts.urls")),
    path("correlation/", include("correlation.urls")),
    path("dashboard/", DashboardView.as_view(), name="dashboard"),
    path("dashboard/", include("dashboard.urls")),
    path("reports/", include("reports.urls")),
    path("investigations/", TemplateView.as_view(template_name="investigations.html"), name="investigations"),
    path("settings/", TemplateView.as_view(template_name="settings.html"), name="settings"),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
