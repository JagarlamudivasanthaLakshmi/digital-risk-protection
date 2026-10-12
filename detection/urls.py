from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import ExplainableRiskView, RiskFindingViewSet

router = DefaultRouter()
router.register("api/findings", RiskFindingViewSet, basename="risk-finding")

urlpatterns = [
    path("analysis/", ExplainableRiskView.as_view(), name="risk-analysis"),
    path("", include(router.urls)),
]
