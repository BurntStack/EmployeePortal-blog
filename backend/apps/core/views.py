from django.utils import timezone
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.reverse import reverse
from rest_framework.throttling import ScopedRateThrottle
from rest_framework_simplejwt.views import TokenObtainPairView


class ThrottledTokenObtainPairView(TokenObtainPairView):
    """Login, with a stricter throttle than the generic anon rate — this is
    the one endpoint that's actually gating password guesses."""

    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "login"


@api_view(["GET"])
@permission_classes([AllowAny])
def health_check(request):
    """Lightweight liveness probe for load balancers / uptime monitors."""
    return Response({"status": "ok", "time": timezone.now().isoformat()})


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def me(request):
    """Who's logged in — the portal uses this to decide what to show."""
    user = request.user
    return Response(
        {
            "id": user.id,
            "username": user.username,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "email": user.email,
            "is_staff": user.is_staff,
        }
    )


@api_view(["GET"])
@permission_classes([AllowAny])
def api_root(request, format=None):
    """Browsable index of the available API endpoints."""
    return Response(
        {
            "health": reverse("health", request=request, format=format),
            "auth": {
                "token": reverse("token_obtain_pair", request=request, format=format),
                "refresh": reverse("token_refresh", request=request, format=format),
                "verify": reverse("token_verify", request=request, format=format),
                "me": reverse("me", request=request, format=format),
            },
            "blog": reverse("post-list", request=request, format=format),
            "categories": reverse("category-list", request=request, format=format),
            "portal_blog": reverse("employee-post-list", request=request, format=format),
        }
    )
