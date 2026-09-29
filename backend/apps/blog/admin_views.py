"""Authenticated editorial administration, with independently enforced permissions."""
from datetime import timedelta

from django.contrib.auth.models import User
from django.db import transaction
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import serializers, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework.throttling import AnonRateThrottle
from rest_framework.views import APIView

from . import editorial
from .models import Activity, Category, EditorialSettings, Membership, Notification, Post, ReadEvent
from .permissions import IsAdmin, IsReviewer, can_review, role_for
from .serializers import CategorySerializer, PostWriteSerializer


def user_data(user):
    return {"id": user.id, "name": user.get_full_name() or user.username, "email": user.email,
            "role": role_for(user) if user.is_active else (getattr(getattr(user, "portal_membership", None), "role", "admin" if user.is_staff else "contributor")),
            "is_active": user.is_active, "last_login": user.last_login}


class PeopleViewSet(viewsets.GenericViewSet):
    permission_classes = [IsAuthenticated, IsAdmin]
    queryset = User.objects.select_related("portal_membership").order_by("first_name", "username")
    search_fields = ["username", "email", "first_name", "last_name"]

    def list(self, request):
        page = self.paginate_queryset(self.filter_queryset(self.get_queryset()))
        return self.get_paginated_response([user_data(u) for u in page])

    @transaction.atomic
    def partial_update(self, request, pk=None):
        # Lock admins in a consistent order as well as the target, preventing two
        # concurrent demotions from removing all administrators.
        list(User.objects.select_for_update().order_by("id").values_list("id", flat=True))
        user = self.get_object()
        role = serializers.ChoiceField(choices=Membership.Role.choices).run_validation(request.data.get("role", user_data(user)["role"]))
        active = serializers.BooleanField().run_validation(request.data.get("is_active", user.is_active))
        if user.is_superuser and (role != "admin" or not active):
            raise ValidationError("A recovery superuser cannot be disabled or demoted here.")
        if user.id == request.user.id and (role != "admin" or not active):
            raise ValidationError("You cannot remove your own administrator access.")
        settings, _ = EditorialSettings.objects.get_or_create(pk=1)
        if user.id in (settings.primary_admin_id, settings.backup_admin_id) and (role != "admin" or not active):
            raise ValidationError("Reassign primary or backup ownership before changing this administrator.")
        before = {"role": user_data(user)["role"], "is_active": user.is_active}
        Membership.objects.update_or_create(user=user, defaults={"role": role})
        user.is_staff, user.is_active = role == "admin", active
        user.save(update_fields=["is_staff", "is_active"])
        # Inactive users cannot authenticate with existing access JWTs. Revoke refreshes too.
        if not active:
            from rest_framework_simplejwt.token_blacklist.models import OutstandingToken, BlacklistedToken
            for token in OutstandingToken.objects.filter(user=user):
                BlacklistedToken.objects.get_or_create(token=token)
        editorial.audit(request.user, "access_changed", target=user.username, before=before, after={"role": role, "is_active": active})
        user.refresh_from_db()
        return Response(user_data(user))


class ManageCategoryViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated, IsAdmin]
    queryset = Category.objects.all()
    serializer_class = CategorySerializer

    @transaction.atomic
    def perform_create(self, serializer):
        obj = serializer.save()
        editorial.audit(self.request.user, "category_created", target=obj.name)

    @transaction.atomic
    def perform_update(self, serializer):
        obj = serializer.save()
        editorial.audit(self.request.user, "category_updated", target=obj.name)

    @transaction.atomic
    def perform_destroy(self, instance):
        if instance.posts.exists() or Post.objects.filter(published_revision__snapshot__category__id=instance.id).exists():
            raise ValidationError("This category is used by a post. Reassign and republish those posts before deleting it.")
        editorial.audit(self.request.user, "category_deleted", target=instance.name)
        instance.delete()


class ActivitySerializer(serializers.ModelSerializer):
    class Meta:
        model = Activity
        fields = ["id", "actor_name", "action", "target", "details", "created_at"]


class ActivityViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [IsAuthenticated, IsAdmin]
    queryset = Activity.objects.all()
    serializer_class = ActivitySerializer
    search_fields = ["actor_name", "action", "target"]
    filterset_fields = ["action"]


class NotificationSerializer(serializers.ModelSerializer):
    slug = serializers.CharField(source="post.slug", read_only=True, default=None)

    class Meta:
        model = Notification
        fields = ["id", "message", "slug", "read_at", "created_at"]


class NotificationViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = NotificationSerializer

    def get_queryset(self):
        return Notification.objects.filter(recipient=self.request.user).select_related("post")

    @action(detail=False, methods=["post"], url_path="read-all")
    def read_all(self, request):
        self.get_queryset().filter(read_at__isnull=True).update(read_at=timezone.now())
        return Response({"detail": "Notifications marked as read."})

    @action(detail=True, methods=["post"])
    def read(self, request, pk=None):
        obj = self.get_object()
        obj.read_at = timezone.now()
        obj.save(update_fields=["read_at"])
        return Response(self.get_serializer(obj).data)


class SettingsSerializer(serializers.ModelSerializer):
    class Meta:
        model = EditorialSettings
        fields = ["primary_admin", "backup_admin", "review_days", "guidelines"]

    def validate(self, attrs):
        for field in ("primary_admin", "backup_admin"):
            user = attrs.get(field, getattr(self.instance, field, None))
            if user and role_for(user) != "admin":
                raise ValidationError({field: "Select an active administrator."})
        primary = attrs.get("primary_admin", getattr(self.instance, "primary_admin", None))
        backup = attrs.get("backup_admin", getattr(self.instance, "backup_admin", None))
        if primary and primary == backup:
            raise ValidationError("Primary and backup must be different people.")
        if not 1 <= attrs.get("review_days", getattr(self.instance, "review_days", 3)) <= 30:
            raise ValidationError("Review target must be between 1 and 30 days.")
        return attrs


class SettingsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        obj, _ = EditorialSettings.objects.get_or_create(pk=1)
        return Response(SettingsSerializer(obj).data)

    @transaction.atomic
    def patch(self, request):
        if role_for(request.user) != "admin":
            self.permission_denied(request)
        obj, _ = EditorialSettings.objects.get_or_create(pk=1)
        serializer = SettingsSerializer(obj, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        editorial.audit(request.user, "editorial_settings_changed", target="Editorial settings")
        return Response(serializer.data)


class OverviewView(APIView):
    permission_classes = [IsAuthenticated, IsReviewer]

    def get(self, request):
        editorial.publish_due()
        editorial.send_reminders()
        settings, _ = EditorialSettings.objects.get_or_create(pk=1)
        cutoff = timezone.now() - timedelta(days=settings.review_days)
        counts = dict(Post.objects.values_list("status").annotate(total=Count("id")))
        pending = Post.objects.filter(status="pending")
        return Response({"counts": counts, "live": Post.objects.filter(published_revision__isnull=False).count(),
                         "overdue": pending.filter(submitted_at__lte=cutoff).count(), "unassigned": pending.filter(reviewer__isnull=True).count(),
                         "my_reviews": pending.filter(reviewer=request.user).count(),
                         "recent": PostWriteSerializer(Post.objects.select_related("author", "category", "reviewer").order_by("-updated_at")[:6], many=True, context={"request": request}).data,
                         "authors": [{"id": u.id, "name": u.get_full_name() or u.username} for u in User.objects.filter(posts__isnull=False).distinct().order_by("username")],
                         "reviewers": [user_data(u) for u in User.objects.filter(is_active=True).select_related("portal_membership") if can_review(u)],
                         "settings": SettingsSerializer(settings).data})


class AnalyticsView(APIView):
    permission_classes = [IsAuthenticated, IsReviewer]

    def get(self, request):
        start = timezone.localdate() - timedelta(days=29)
        events = ReadEvent.objects.filter(day__gte=start)
        totals = events.aggregate(views=Count("id"), engaged=Count("id", filter=Q(engaged=True)))
        performance = list(events.values("post__slug", "post__title").annotate(views=Count("id"), engaged=Count("id", filter=Q(engaged=True))).order_by("-views")[:20])
        # Match each decision to its latest preceding submission, including re-submissions.
        hours = []
        for event in Activity.objects.filter(action__in=["published", "scheduled", "changes_requested", "rejected"], actor__isnull=False, created_at__date__gte=start, post__isnull=False).order_by("-created_at")[:500]:
            submitted = Activity.objects.filter(post_id=event.post_id, action="submitted", created_at__lte=event.created_at).order_by("-created_at").first()
            if submitted:
                hours.append((event.created_at - submitted.created_at).total_seconds() / 3600)
        return Response({"days": 30, **totals, "engagement_rate": round(totals["engaged"] / totals["views"] * 100, 1) if totals["views"] else 0,
                         "average_review_hours": round(sum(hours) / len(hours), 1) if hours else None, "review_decisions": len(hours),
                         "daily": list(events.values("day").annotate(views=Count("id"), engaged=Count("id", filter=Q(engaged=True))).order_by("day")),
                         "posts": performance, "definition": "Views count once per article, random browser session and day. Engaged reads require 30 seconds on the page and 50% scroll. Review turnaround uses up to 500 recent decisions."})


class ReadEventView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]
    throttle_classes = [AnonRateThrottle]

    def post(self, request, slug):
        post = get_object_or_404(Post, slug=slug, published_revision__isnull=False)
        session = serializers.UUIDField().run_validation(request.data.get("session"))
        engaged = serializers.BooleanField().run_validation(request.data.get("engaged", False))
        event, _ = ReadEvent.objects.get_or_create(post=post, session=session, day=timezone.localdate())
        if engaged and not event.engaged:
            event.engaged = True
            event.save(update_fields=["engaged"])
        return Response({"recorded": True}, status=202)


class EditorialJobsView(APIView):
    """Cron entry point. The secret is deployment configuration, never a user token."""
    authentication_classes = []
    permission_classes = [AllowAny]
    throttle_classes = []

    def get(self, request):
        import secrets
        from django.conf import settings
        secret = settings.EDITORIAL_CRON_SECRET
        if not secret or not secrets.compare_digest(request.headers.get("Authorization", ""), f"Bearer {secret}"):
            return Response({"detail": "Invalid scheduler credentials."}, status=403)
        return Response({"published": editorial.publish_due(), "overdue": editorial.send_reminders()})
