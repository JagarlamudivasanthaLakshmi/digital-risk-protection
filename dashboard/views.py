from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import TemplateView
from django.db.models import Q
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from brands.models import Brand
from monitoring.models import MonitoredItem

from .serializers import DashboardStatsSerializer
from .services import dashboard_stats


class DashboardView(LoginRequiredMixin, TemplateView):
    template_name = "dashboard.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(dashboard_stats(self.request.user))
        query = self.request.GET.get("q", "").strip()
        context["search_query"] = query
        if query:
            brand_results = [
                {
                    "title": brand.name,
                    "description": "Brand profile",
                    "url": "/brands/",
                    "kind": "Brand",
                }
                for brand in Brand.objects.filter(owner=self.request.user)
                .filter(Q(name__icontains=query) | Q(description__icontains=query))[:5]
            ]
            domain_matches = []
            for brand in Brand.objects.filter(owner=self.request.user).only(
                "name", "official_domains"
            ):
                if any(query.casefold() in domain.casefold() for domain in brand.official_domains):
                    domain_matches.append({
                        "title": brand.name,
                        "description": ", ".join(brand.official_domains),
                        "url": "/brands/",
                        "kind": "Official domain",
                    })

            monitored_results = [
                {
                    "title": item.name,
                    "description": item.url or item.get_source_display(),
                    "url": (
                        "/monitoring/apps/"
                        if item.source in (
                            MonitoredItem.Source.SOCIAL,
                            MonitoredItem.Source.INSTAGRAM,
                            MonitoredItem.Source.FACEBOOK,
                            MonitoredItem.Source.X,
                            MonitoredItem.Source.LINKEDIN,
                            MonitoredItem.Source.YOUTUBE,
                            MonitoredItem.Source.TIKTOK,
                            MonitoredItem.Source.APP_STORE,
                            MonitoredItem.Source.GOOGLE_PLAY,
                        )
                        else "/monitoring/social/"
                    ),
                    "kind": item.get_source_display(),
                }
                for item in MonitoredItem.objects.filter(brand__owner=self.request.user)
                .filter(
                    Q(name__icontains=query)
                    | Q(url__icontains=query)
                    | Q(publisher__icontains=query)
                    | Q(content__icontains=query)
                )
                .select_related("brand")[:8]
            ]
            context["search_results"] = (brand_results + domain_matches + monitored_results)[:10]
        return context


class DashboardStatsAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response(DashboardStatsSerializer(dashboard_stats(request.user)).data)
