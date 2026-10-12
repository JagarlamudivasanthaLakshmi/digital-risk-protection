from django.urls import path

from .views import FindingsCSVView, ReportsView

urlpatterns = [
    path("", ReportsView.as_view(), name="reports"),
    path("findings.csv", FindingsCSVView.as_view(), name="findings-csv"),
]
