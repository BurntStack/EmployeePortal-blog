from django.urls import path
from rest_framework.routers import DefaultRouter

from .admin_views import (PeopleViewSet, ManageCategoryViewSet, ActivityViewSet, NotificationViewSet, SettingsView, OverviewView, AnalyticsView, ReadEventView)

from .views import CategoryViewSet, ContentImageUploadView, EmployeePostViewSet, PostViewSet

# Public, read-only.
router = DefaultRouter()
router.register("categories", CategoryViewSet, basename="category")
router.register("", PostViewSet, basename="post")

# Authenticated portal — an employee's own posts plus admin review actions.
portal_router = DefaultRouter()
portal_router.register("", EmployeePostViewSet, basename="employee-post")

admin_router = DefaultRouter()
admin_router.register("people", PeopleViewSet, basename="portal-people")
admin_router.register("categories", ManageCategoryViewSet, basename="portal-categories")
admin_router.register("activity", ActivityViewSet, basename="portal-activity")
admin_router.register("notifications", NotificationViewSet, basename="portal-notifications")

admin_urlpatterns = [
    path("overview/", OverviewView.as_view()),
    path("settings/", SettingsView.as_view()),
    path("analytics/", AnalyticsView.as_view()),
] + admin_router.urls

urlpatterns = [path("<slug:slug>/events/", ReadEventView.as_view())] + router.urls

portal_urlpatterns = [
    path("uploads/image/", ContentImageUploadView.as_view(), name="content-image-upload"),
] + portal_router.urls
