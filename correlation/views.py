from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import TemplateView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .services import graph_for_user


class ThreatGraphView(LoginRequiredMixin, TemplateView):
    template_name = "threat_graph.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["graph"] = graph_for_user(self.request.user)
        return context


class ThreatGraphAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response(graph_for_user(request.user))
