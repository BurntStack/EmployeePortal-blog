"""Root URL configuration for the BurntStack Employee Portal API."""

from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from rest_framework_simplejwt.views import TokenRefreshView, TokenVerifyView

from apps.blog.urls import portal_urlpatterns as blog_portal_urlpatterns
from apps.core.views import ThrottledTokenObtainPairView, api_root, health_check, me

api_patterns = [
    path("", api_root, name="api-root"),
    path("health/", health_check, name="health"),
    # JWT authentication
    path("auth/token/", ThrottledTokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("auth/token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    path("auth/token/verify/", TokenVerifyView.as_view(), name="token_verify"),
    path("auth/me/", me, name="me"),
    # Public, read-only feed — this is what burntstack.com/blog fetches.
    path("blog/", include("apps.blog.urls")),
    # Employee portal — authenticated blog CRUD + review workflow.
    path("portal/blog/", include(blog_portal_urlpatterns)),
]

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/", include(api_patterns)),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

# Branded admin
admin.site.site_header = "BurntStack Employee Portal Administration"
admin.site.site_title = "BurntStack Portal Admin"
admin.site.index_title = "Dashboard"
