from django.urls import path

from .views import ThreatGraphAPIView, ThreatGraphView

urlpatterns = [
    path("", ThreatGraphView.as_view(), name="threat-graph"),
    path("api/", ThreatGraphAPIView.as_view(), name="threat-graph-api"),
]
