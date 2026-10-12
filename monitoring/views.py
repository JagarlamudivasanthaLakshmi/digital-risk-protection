from django.conf import settings
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.shortcuts import redirect
from django.views import View
from django.views.generic import ListView
from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from brands.models import Brand
from detection.services import record_finding
from .collectors.providers import (
    CollectorError,
    official_app_matches,
    official_url_matches,
)
from .forms import MANUAL_SOCIAL_SOURCES, ManualMonitoredItemForm, MonitoringScanForm
from .models import SOCIAL_SOURCE_VALUES, MonitoredItem
from .serializers import MonitoredItemSerializer, MonitoringScanSerializer
from .services import scan_brand


class MonitoredItemViewSet(viewsets.ModelViewSet):
    serializer_class = MonitoredItemSerializer

    def get_queryset(self):
        return MonitoredItem.objects.filter(brand__owner=self.request.user).select_related("brand")


class MonitoringPageView(LoginRequiredMixin, ListView):
    model = MonitoredItem
    template_name = "social_monitoring.html"
    context_object_name = "items"

    def get_queryset(self):
        return MonitoredItem.objects.filter(
            brand__owner=self.request.user, source__in=SOCIAL_SOURCE_VALUES
        ).select_related("brand").prefetch_related("findings")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["scan_form"] = MonitoringScanForm(
            self.request.user, source=MonitoredItem.Source.SOCIAL
        )
        context["item_form"] = ManualMonitoredItemForm(
            self.request.user, source=MonitoredItem.Source.SOCIAL
        )
        context["brands"] = Brand.objects.filter(owner=self.request.user)
        context["MASTODON_INSTANCES"] = settings.MASTODON_INSTANCES
        context["manual_social_sources"] = MANUAL_SOCIAL_SOURCES
        return context


class AppMonitoringPageView(MonitoringPageView):
    template_name = "app_monitoring.html"

    def get_queryset(self):
        return MonitoredItem.objects.filter(
            brand__owner=self.request.user,
            source__in=(MonitoredItem.Source.APP_STORE, MonitoredItem.Source.GOOGLE_PLAY),
        ).select_related("brand").prefetch_related("findings")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["scan_form"] = MonitoringScanForm(
            self.request.user, source=MonitoredItem.Source.APP_STORE
        )
        context["item_form"] = ManualMonitoredItemForm(
            self.request.user, source=MonitoredItem.Source.APP_STORE
        )
        context["brands"] = Brand.objects.filter(owner=self.request.user)
        context["APPLE_APP_STORE_COUNTRY"] = settings.APPLE_APP_STORE_COUNTRY
        context["GOOGLE_PLAY_COUNTRY"] = settings.GOOGLE_PLAY_COUNTRY
        context["GOOGLE_PLAY_LANGUAGE"] = settings.GOOGLE_PLAY_LANGUAGE
        return context


class MonitoringScanView(LoginRequiredMixin, View):
    def post(self, request):
        source = request.POST.get("source", "")
        form = MonitoringScanForm(request.user, request.POST, source=source)
        if not form.is_valid():
            for errors in form.errors.values():
                for error in errors:
                    messages.error(request, error)
            return redirect(self._page_for_source(source))
        brand = form.cleaned_data["brand"]
        try:
            result = scan_brand(brand, form.cleaned_data["source"])
        except CollectorError as exc:
            messages.error(request, str(exc))
        else:
            messages.success(
                request,
                f"Scanned {brand.name}: {result['found']} candidates found, "
                f"{result['new']} new, {result['updated']} updated, "
                f"{result['alerts']} alerts created.",
            )
            for warning in result["warnings"]:
                messages.warning(request, warning)
        return redirect(self._page_for_source(source))

    @staticmethod
    def _page_for_source(source):
        if source in (MonitoredItem.Source.APP_STORE, MonitoredItem.Source.GOOGLE_PLAY):
            return "app-monitoring"
        return "social-monitoring"


class MonitoringScanAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = MonitoringScanSerializer(
            data=request.data, context={"request": request}
        )
        serializer.is_valid(raise_exception=True)
        try:
            result = scan_brand(
                serializer.validated_data["brand"],
                serializer.validated_data["source"],
                limit=serializer.validated_data["limit"],
            )
        except CollectorError as exc:
            return Response({"detail": str(exc)}, status=502)
        return Response({
            "found": result["found"],
            "new": result["new"],
            "updated": result["updated"],
            "scored": result["scored"],
            "alerts": result["alerts"],
            "warnings": result["warnings"],
        })


class ManualMonitoredItemCreateView(LoginRequiredMixin, View):
    def post(self, request):
        source = request.POST.get("source", "")
        form = ManualMonitoredItemForm(request.user, request.POST, source=source)
        if not form.is_valid():
            for errors in form.errors.values():
                for error in errors:
                    messages.error(request, error)
            return redirect(MonitoringScanView._page_for_source(source))

        brand = form.cleaned_data["brand"]
        source = form.cleaned_data["source"]
        url = form.cleaned_data.get("url", "")
        if source in SOCIAL_SOURCE_VALUES and url and official_url_matches(
            url, brand.official_social_accounts
        ):
            messages.error(
                request,
                "This URL is already listed as an official brand social account.",
            )
            return redirect(MonitoringScanView._page_for_source(source))
        if source in (
            MonitoredItem.Source.APP_STORE,
            MonitoredItem.Source.GOOGLE_PLAY,
        ) and official_app_matches(
            {
                "url": url,
                "external_id": "",
                "metadata": {},
            },
            brand.official_apps,
        ):
            messages.error(request, "This app is already listed as an official brand asset.")
            return redirect(MonitoringScanView._page_for_source(source))
        item = MonitoredItem.objects.create(
            brand=brand,
            source=source,
            name=form.cleaned_data["name"],
            url=form.cleaned_data.get("url", ""),
            publisher=form.cleaned_data.get("publisher", ""),
            content=form.cleaned_data.get("content", ""),
        )
        finding, alert_created = record_finding(item)
        messages.success(
            request,
            f"Added {item.name} and scored it at {finding.risk_score}/100 "
            f"({finding.get_severity_display()})."
            + (" An alert was created." if alert_created else ""),
        )
        return redirect(MonitoringScanView._page_for_source(source))
