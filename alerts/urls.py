from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import AlertDetailView, AlertListView, AlertUpdateView, AlertViewSet

router = DefaultRouter()
router.register("api", AlertViewSet, basename="alert-api")

urlpatterns = [
    path("", AlertListView.as_view(), name="alert-list"),
    path("<int:pk>/", AlertDetailView.as_view(), name="alert-detail"),
    path("<int:pk>/update/", AlertUpdateView.as_view(), name="alert-update"),
    path("", include(router.urls)),
]
