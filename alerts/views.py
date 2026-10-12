from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.shortcuts import get_object_or_404
from django.shortcuts import redirect
from django.views import View
from django.views.generic import DetailView, ListView
from rest_framework import viewsets

from services.ai_explainer import explain_finding
from .forms import AlertUpdateForm
from .filters import filter_alerts
from .models import Alert
from .serializers import AlertSerializer


class AlertViewSet(viewsets.ModelViewSet):
    serializer_class = AlertSerializer
    http_method_names = ("get", "patch", "head", "options")

    def get_queryset(self):
        queryset = Alert.objects.filter(finding__brand__owner=self.request.user).select_related(
            "finding", "finding__brand"
        )
        return filter_alerts(queryset, self.request.query_params)


class AlertListView(LoginRequiredMixin, ListView):
    model = Alert
    template_name = "alerts.html"
    context_object_name = "alerts"

    def get_queryset(self):
        queryset = Alert.objects.filter(
            finding__brand__owner=self.request.user
        ).select_related("finding", "finding__brand", "finding__monitored_item")
        return filter_alerts(queryset, self.request.GET)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["alert_status_choices"] = Alert.Status.choices
        context["severity_choices"] = (
            ("low", "Low"),
            ("medium", "Medium"),
            ("high", "High"),
            ("critical", "Critical"),
        )
        return context


class AlertDetailView(LoginRequiredMixin, DetailView):
    model = Alert
    template_name = "alert_details.html"
    context_object_name = "alert"

    def get_object(self, queryset=None):
        return get_object_or_404(
            Alert.objects.select_related("finding", "finding__brand"),
            pk=self.kwargs["pk"],
            finding__brand__owner=self.request.user,
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["risk_explanation"] = explain_finding(context["alert"].finding)
        context["update_form"] = AlertUpdateForm(instance=context["alert"])
        return context


class AlertUpdateView(LoginRequiredMixin, View):
    def post(self, request, pk):
        alert = get_object_or_404(
            Alert.objects.filter(finding__brand__owner=request.user),
            pk=pk,
        )
        form = AlertUpdateForm(request.POST, instance=alert)
        if form.is_valid():
            form.save()
            messages.success(request, "Investigation updated.")
        else:
            for errors in form.errors.values():
                for error in errors:
                    messages.error(request, error)
        return redirect("alert-detail", pk=pk)
