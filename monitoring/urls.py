from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    AppMonitoringPageView,
    ManualMonitoredItemCreateView,
    MonitoredItemViewSet,
    MonitoringPageView,
    MonitoringScanAPIView,
    MonitoringScanView,
)

router = DefaultRouter()
router.register("api/items", MonitoredItemViewSet, basename="monitored-item")

urlpatterns = [
    path("social/", MonitoringPageView.as_view(), name="social-monitoring"),
    path("apps/", AppMonitoringPageView.as_view(), name="app-monitoring"),
    path("scan/", MonitoringScanView.as_view(), name="monitoring-scan"),
    path("items/add/", ManualMonitoredItemCreateView.as_view(), name="monitoring-item-create"),
    path("api/scan/", MonitoringScanAPIView.as_view(), name="monitoring-scan-api"),
    path("", include(router.urls)),
]
