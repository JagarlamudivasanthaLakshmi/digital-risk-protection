from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import CreateView, ListView, UpdateView
from rest_framework import viewsets

from .models import Brand
from .forms import BrandProfileForm
from .serializers import BrandSerializer


class BrandViewSet(viewsets.ModelViewSet):
    serializer_class = BrandSerializer

    def get_queryset(self):
        return Brand.objects.filter(owner=self.request.user)

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)


class BrandListView(LoginRequiredMixin, ListView):
    model = Brand
    template_name = "brand_profiles.html"
    context_object_name = "brands"

    def get_queryset(self):
        return Brand.objects.filter(owner=self.request.user)


class BrandCreateView(LoginRequiredMixin, CreateView):
    model = Brand
    form_class = BrandProfileForm
    template_name = "add_brand.html"
    success_url = "/brands/"

    def form_valid(self, form):
        form.instance.owner = self.request.user
        return super().form_valid(form)


class BrandUpdateView(LoginRequiredMixin, UpdateView):
    model = Brand
    form_class = BrandProfileForm
    template_name = "add_brand.html"
    success_url = "/brands/"

    def get_queryset(self):
        return Brand.objects.filter(owner=self.request.user)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["editing"] = True
        return context
