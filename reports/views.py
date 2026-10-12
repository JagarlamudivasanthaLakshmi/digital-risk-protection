from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpResponse
from django.views.generic import TemplateView, View

from .services import user_findings_csv


class ReportsView(LoginRequiredMixin, TemplateView):
    template_name = "reports.html"


class FindingsCSVView(LoginRequiredMixin, View):
    def get(self, request):
        response = HttpResponse(user_findings_csv(request.user), content_type="text/csv")
        response["Content-Disposition"] = 'attachment; filename="risk-findings.csv"'
        return response
