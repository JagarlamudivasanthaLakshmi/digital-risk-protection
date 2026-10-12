from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import ListView
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from monitoring.models import MonitoredItem
from .services import record_finding
from .models import RiskFinding
from .serializers import RiskFindingSerializer


class RiskFindingViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = RiskFindingSerializer

    def get_queryset(self):
        return RiskFinding.objects.filter(brand__owner=self.request.user).select_related(
            "brand", "monitored_item"
        )

    @action(detail=False, methods=["post"])
    def scan(self, request):
        item_id = request.data.get("item_id")
        try:
            item = MonitoredItem.objects.select_related("brand").get(
                pk=item_id, brand__owner=request.user
            )
        except (MonitoredItem.DoesNotExist, ValueError, TypeError):
            return Response({"detail": "A valid item_id belonging to your account is required."}, status=400)
        finding, _ = record_finding(item)
        return Response(self.get_serializer(finding).data, status=201)


class ExplainableRiskView(LoginRequiredMixin, ListView):
    model = RiskFinding
    template_name = "explainable_risk.html"
    context_object_name = "findings"

    def get_queryset(self):
        return RiskFinding.objects.filter(brand__owner=self.request.user).select_related("brand", "monitored_item")
