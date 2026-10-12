from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import BrandCreateView, BrandListView, BrandUpdateView, BrandViewSet

router = DefaultRouter()
router.register("api", BrandViewSet, basename="brand-api")

urlpatterns = [
    path("", BrandListView.as_view(), name="brand-list"),
    path("add/", BrandCreateView.as_view(), name="brand-create"),
    path("<int:pk>/edit/", BrandUpdateView.as_view(), name="brand-edit"),
    path("", include(router.urls)),
]
