from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import CategoryViewSet, ContentImageUploadView, EmployeePostViewSet, PostViewSet

# Public, read-only.
router = DefaultRouter()
router.register("categories", CategoryViewSet, basename="category")
router.register("", PostViewSet, basename="post")

# Authenticated portal — an employee's own posts plus admin review actions.
portal_router = DefaultRouter()
portal_router.register("", EmployeePostViewSet, basename="employee-post")

urlpatterns = router.urls

portal_urlpatterns = [
    path("uploads/image/", ContentImageUploadView.as_view(), name="content-image-upload"),
] + portal_router.urls
