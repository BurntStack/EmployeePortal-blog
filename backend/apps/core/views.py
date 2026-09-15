from django.conf import settings
from django.contrib.auth.models import User
from django.utils import timezone
from google.auth.transport import requests as google_requests
from google.oauth2 import id_token as google_id_token
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.reverse import reverse
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView


class ThrottledTokenObtainPairView(TokenObtainPairView):
    """Login, with a stricter throttle than the generic anon rate — this is
    the one endpoint that's actually gating password guesses."""

    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "login"


def verify_google_token(credential):
    """
    Verify a Google ID token and return its decoded claims. Split into its
    own function so tests can monkeypatch it instead of calling out to
    Google's network for every test run.
    """
    return google_id_token.verify_oauth2_token(
        credential, google_requests.Request(), settings.GOOGLE_CLIENT_ID
    )


class GoogleLoginView(APIView):
    """
    Sign in with Google, restricted to a verified @<ALLOWED_EMAIL_DOMAIN>
    account. Auto-provisions a User on first login — the existing
    draft/pending/published approval workflow is what still gates content,
    this only gates who can log in at all. Returns the same {access,
    refresh} shape as the password endpoint, so the frontend treats both
    login paths identically.
    """

    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "login"

    def post(self, request):
        if not settings.GOOGLE_CLIENT_ID:
            return Response(
                {"detail": "Google sign-in is not configured."},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        credential = request.data.get("credential")
        if not credential:
            return Response({"detail": "Missing credential."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            payload = verify_google_token(credential)
        except ValueError:
            return Response({"detail": "Invalid Google credential."}, status=status.HTTP_401_UNAUTHORIZED)

        domain = settings.ALLOWED_EMAIL_DOMAIN
        email = (payload.get("email") or "").lower()
        email_verified = bool(payload.get("email_verified"))
        hosted_domain = payload.get("hd") or ""

        # The `hd` claim is Google's authoritative signal for a Workspace
        # domain; the suffix check is free defense in depth alongside it.
        if not email_verified or hosted_domain != domain or not email.endswith(f"@{domain}"):
            return Response(
                {"detail": f"Only verified @{domain} Google accounts can sign in."},
                status=status.HTTP_403_FORBIDDEN,
            )

        is_admin = email in {e.lower() for e in settings.ADMIN_EMAILS}
        user, _ = User.objects.get_or_create(
            username=email,
            defaults={
                "email": email,
                "first_name": payload.get("given_name", ""),
                "last_name": payload.get("family_name", ""),
            },
        )
        if user.is_staff != is_admin:
            user.is_staff = is_admin
            user.save(update_fields=["is_staff"])

        refresh = RefreshToken.for_user(user)
        return Response({"access": str(refresh.access_token), "refresh": str(refresh)})


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
                "google": reverse("google_login", request=request, format=format),
                "verify": reverse("token_verify", request=request, format=format),
                "me": reverse("me", request=request, format=format),
            },
            "blog": reverse("post-list", request=request, format=format),
            "categories": reverse("category-list", request=request, format=format),
            "portal_blog": reverse("employee-post-list", request=request, format=format),
        }
    )
