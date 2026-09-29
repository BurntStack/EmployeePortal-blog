import logging
import uuid

from django.core.files.storage import default_storage
from django.utils import timezone
from rest_framework import status as http_status
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.parsers import MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Category, Post
from .permissions import IsAdmin, IsOwnerOrAdmin
from .serializers import (
    CategorySerializer,
    PostDetailSerializer,
    PostListSerializer,
    PostWriteSerializer,
)

logger = logging.getLogger(__name__)

ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/gif", "image/webp", "image/avif"}
MAX_UPLOAD_BYTES = 8 * 1024 * 1024  # 8MB


class ContentImageUploadView(APIView):
    """
    Image upload for the rich text editor. Drag-drop, paste, and the
    toolbar's image button all POST here and embed the returned URL in the
    post's HTML content, instead of inlining base64 image data in `content`
    itself (which would bloat every request and the stored row).
    """

    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser]

    def post(self, request):
        image = request.FILES.get("image")
        if not image:
            return Response({"detail": "No image file provided."}, status=http_status.HTTP_400_BAD_REQUEST)
        if image.content_type not in ALLOWED_IMAGE_TYPES:
            return Response({"detail": "Unsupported image type."}, status=http_status.HTTP_400_BAD_REQUEST)
        if image.size > MAX_UPLOAD_BYTES:
            return Response({"detail": "Image is too large (max 8MB)."}, status=http_status.HTTP_400_BAD_REQUEST)
        ext = image.name.rsplit(".", 1)[-1].lower() if "." in image.name else "jpg"
        try:
            path = default_storage.save(f"blog-content/{uuid.uuid4().hex}.{ext}", image)
            # Remote storage returns an absolute URL and build_absolute_uri
            # passes it through untouched; the local-disk fallback returns
            # "/media/..." and needs the host prepended.
            url = request.build_absolute_uri(default_storage.url(path))
        except Exception:
            # Misconfigured or unreachable object storage. Without this the
            # author gets a bare 500 and the editor shows a generic failure,
            # which is indistinguishable from "the button does nothing".
            logger.exception("Content image upload failed for user %s", request.user)
            return Response(
                {"detail": "Image storage is unavailable right now. Please try again."},
                status=http_status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        return Response({"url": url}, status=http_status.HTTP_201_CREATED)


from django.db import transaction
from django.db.models import Q
from django.shortcuts import get_object_or_404
from rest_framework.exceptions import ValidationError
from rest_framework import serializers
from .sanitize import clean_post_html
from . import editorial
from .models import Revision, ReviewComment
from .permissions import IsReviewer, can_review


class CategoryViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    pagination_class = None


class PostViewSet(viewsets.ReadOnlyModelViewSet):
    lookup_field = "slug"
    filter_backends = []

    def get_queryset(self):
        editorial.publish_due()
        qs = Post.objects.filter(published_revision__isnull=False).select_related("published_revision", "author")
        params = self.request.query_params
        if params.get("category__slug"):
            qs = qs.filter(published_revision__snapshot__category__slug=params["category__slug"])
        if params.get("is_featured") in ("true", "false", "True", "False"):
            qs = qs.filter(is_featured=params["is_featured"].lower() == "true")
        if params.get("search"):
            query = params["search"][:200]
            qs = qs.filter(Q(published_revision__snapshot__title__icontains=query) | Q(published_revision__snapshot__excerpt__icontains=query) | Q(published_revision__snapshot__content__icontains=query))
        order = params.get("ordering", "-published_at")
        ordering = {"published_at": "published_at", "-published_at": "-published_at", "reading_time": "published_revision__snapshot__reading_time", "-reading_time": "-published_revision__snapshot__reading_time"}
        return qs.order_by(ordering.get(order, "-published_at"), "-id")

    def get_serializer_class(self):
        return PostDetailSerializer if self.action == "retrieve" else PostListSerializer


class EmployeePostViewSet(viewsets.ModelViewSet):
    serializer_class = PostWriteSerializer
    permission_classes = [IsAuthenticated, IsOwnerOrAdmin]
    lookup_field = "slug"
    filterset_fields = ["status", "category__slug", "author", "reviewer", "is_featured"]
    search_fields = ["title", "excerpt", "content", "tags"]
    ordering_fields = ["created_at", "updated_at", "published_at", "scheduled_at", "submitted_at"]
    ordering = ["-updated_at", "-id"]

    def get_queryset(self):
        qs = Post.objects.select_related("category", "author", "reviewer")
        if not can_review(self.request.user):
            qs = qs.filter(author=self.request.user)
        for param, lookup in (("created_after", "created_at__date__gte"), ("created_before", "created_at__date__lte")):
            if self.request.query_params.get(param):
                date = serializers.DateField().run_validation(self.request.query_params[param])
                qs = qs.filter(**{lookup: date})
        return qs

    def locked_post(self):
        # Do not join nullable reviewer/category relations in SELECT FOR UPDATE (Postgres).
        qs = Post.objects.select_for_update()
        if not can_review(self.request.user):
            qs = qs.filter(author=self.request.user)
        obj = get_object_or_404(qs, slug=self.kwargs["slug"])
        self.check_object_permissions(self.request, obj)
        expected = self.request.data.get("expected_version")
        if self.action in ("approve", "reject", "request_changes", "restore") and expected is None:
            raise ValidationError("Send expected_version so the reviewed revision can be verified.")
        if expected is not None and str(expected) != str(obj.version):
            from rest_framework.exceptions import APIException
            exc = APIException("This post changed since you opened it. Reload before continuing.")
            exc.status_code = 409
            raise exc
        return obj

    @transaction.atomic
    def perform_create(self, serializer):
        serializer.validated_data.pop("expected_version", None)
        post = serializer.save(author=self.request.user)
        editorial.save_revision(post, self.request.user)
        editorial.audit(self.request.user, "created", post)

    @transaction.atomic
    def update(self, request, *args, **kwargs):
        post = self.locked_post()
        serializer = self.get_serializer(post, data=request.data, partial=kwargs.pop("partial", False))
        serializer.is_valid(raise_exception=True)
        serializer.validated_data.pop("expected_version", None)
        post = serializer.save(status=Post.Status.DRAFT, scheduled_at=None, scheduled_revision=None, version=post.version + 1)
        editorial.save_revision(post, request.user)
        editorial.audit(request.user, "edited", post, version=post.version)
        return Response(self.get_serializer(post).data)

    @transaction.atomic
    def destroy(self, request, *args, **kwargs):
        post = self.locked_post()
        if post.published_revision_id or post.status == Post.Status.SCHEDULED:
            raise ValidationError("Unpublish or cancel the scheduled publication before deleting this post.")
        editorial.audit(request.user, "deleted", post)
        post.delete()
        return Response(status=204)

    @action(detail=False, methods=["get"], permission_classes=[IsAuthenticated, IsReviewer])
    def pending(self, request):
        qs = self.filter_queryset(self.get_queryset().filter(status=Post.Status.PENDING))
        return self.get_paginated_response(self.get_serializer(self.paginate_queryset(qs), many=True).data)

    @action(detail=True, methods=["post"])
    @transaction.atomic
    def submit(self, request, slug=None):
        post = self.locked_post()
        if post.status not in (Post.Status.DRAFT, Post.Status.CHANGES_REQUESTED, Post.Status.REJECTED):
            raise ValidationError("Only drafts or returned posts can be submitted.")
        post.status, post.submitted_at = Post.Status.PENDING, timezone.now()
        post.save()
        editorial.audit(request.user, "submitted", post, version=post.version)
        editorial.notify([post.reviewer_id] if post.reviewer_id else editorial.reviewers(), post, f"Ready for review: {post.title}")
        return Response(self.get_serializer(post).data)

    def decision(self, request, decision):
        post = self.locked_post()
        if post.status != Post.Status.PENDING:
            raise ValidationError("Only pending posts can be reviewed.")
        body = serializers.CharField(max_length=4000, allow_blank=decision == "approved").run_validation(request.data.get("body", ""))
        ReviewComment.objects.create(post=post, author=request.user, body=body, decision=decision, version=post.version)
        if decision == "approved":
            revision = post.revisions.filter(number=post.version).first() or editorial.save_revision(post, request.user)
            scheduled_at = request.data.get("scheduled_at")
            if scheduled_at:
                when = serializers.DateTimeField().run_validation(scheduled_at)
                if when <= timezone.now():
                    raise ValidationError("Choose a publication time in the future.")
                post.scheduled_at, post.scheduled_revision, post.status = when, revision, Post.Status.SCHEDULED
                post.save()
                editorial.audit(request.user, "scheduled", post, scheduled_at=when.isoformat(), revision=revision.number)
                editorial.notify([post.author_id], post, f"Approved and scheduled: {post.title}")
            else:
                editorial.publish(post, revision, request.user)
        else:
            post.status = decision
            post.save()
            editorial.audit(request.user, decision, post, version=post.version)
            editorial.notify([post.author_id], post, f"{post.get_status_display()}: {post.title}")
        return Response(self.get_serializer(post).data)

    @action(detail=True, methods=["post"], permission_classes=[IsAuthenticated, IsReviewer])
    @transaction.atomic
    def approve(self, request, slug=None):
        return self.decision(request, "approved")

    @action(detail=True, methods=["post"], permission_classes=[IsAuthenticated, IsReviewer])
    @transaction.atomic
    def reject(self, request, slug=None):
        return self.decision(request, Post.Status.REJECTED)

    @action(detail=True, methods=["post"], url_path="request-changes", permission_classes=[IsAuthenticated, IsReviewer])
    @transaction.atomic
    def request_changes(self, request, slug=None):
        return self.decision(request, Post.Status.CHANGES_REQUESTED)

    @action(detail=True, methods=["get", "post"])
    def comments(self, request, slug=None):
        post = self.get_object()
        if request.method == "POST":
            with transaction.atomic():
                post = self.locked_post()
                body = serializers.CharField(max_length=4000).run_validation(request.data.get("body", ""))
                ReviewComment.objects.create(post=post, author=request.user, body=body, version=post.version)
                editorial.audit(request.user, "commented", post)
                editorial.notify([u for u in [post.author_id, post.reviewer_id] if u != request.user.id], post, f"New feedback: {post.title}")
        return Response([{"id": c.id, "body": c.body, "decision": c.decision, "version": c.version, "author": (c.author.get_full_name() or c.author.username) if c.author else "Former member", "created_at": c.created_at} for c in post.comments.select_related("author")])

    @action(detail=True, methods=["get"])
    def revisions(self, request, slug=None):
        post = self.get_object()
        qs = post.revisions.select_related("created_by")
        page = self.paginate_queryset(qs)
        data = [{"id": r.id, "number": r.number, "snapshot": {**r.snapshot, "content": clean_post_html(r.snapshot['content'])}, "created_at": r.created_at, "author": (r.created_by.get_full_name() or r.created_by.username) if r.created_by else "Former member", "is_live": r.id == post.published_revision_id} for r in page]
        return self.get_paginated_response(data)

    @action(detail=True, methods=["post"])
    @transaction.atomic
    def restore(self, request, slug=None):
        post = self.locked_post()
        revision_id = serializers.IntegerField().run_validation(request.data.get("revision_id"))
        revision = get_object_or_404(Revision, pk=revision_id, post=post)
        data = revision.snapshot
        for field in editorial.CONTENT_FIELDS:
            setattr(post, field, data[field])
        category = data.get("category")
        post.category = Category.objects.filter(pk=category["id"]).first() if category else None
        post.cover_image = data.get("cover_image", "")
        post.version += 1
        post.status, post.scheduled_at, post.scheduled_revision = Post.Status.DRAFT, None, None
        post.save()
        editorial.save_revision(post, request.user)
        editorial.audit(request.user, "restored", post, from_revision=revision.number)
        return Response(self.get_serializer(post).data)

    @action(detail=True, methods=["post"], permission_classes=[IsAuthenticated, IsReviewer])
    @transaction.atomic
    def assign(self, request, slug=None):
        from django.contrib.auth.models import User
        post = self.locked_post()
        reviewer_id = serializers.IntegerField(allow_null=True).run_validation(request.data.get("reviewer_id"))
        reviewer = get_object_or_404(User, pk=reviewer_id, is_active=True) if reviewer_id else None
        if reviewer and not can_review(reviewer):
            raise ValidationError("Assign an active reviewer or administrator.")
        post.reviewer = reviewer
        post.save()
        editorial.audit(request.user, "assigned", post, reviewer_id=reviewer_id)
        editorial.notify([reviewer_id], post, f"Assigned to you: {post.title}")
        return Response(self.get_serializer(post).data)

    @action(detail=True, methods=["post"], permission_classes=[IsAuthenticated, IsReviewer])
    @transaction.atomic
    def unpublish(self, request, slug=None):
        post = self.locked_post()
        post.published_revision, post.published_at, post.scheduled_revision, post.scheduled_at = None, None, None, None
        post.status = Post.Status.ARCHIVED
        post.save()
        editorial.audit(request.user, "unpublished", post)
        editorial.notify([post.author_id], post, f"Unpublished: {post.title}")
        return Response(self.get_serializer(post).data)

    @action(detail=True, methods=["post"], url_path="cancel-schedule", permission_classes=[IsAuthenticated, IsReviewer])
    @transaction.atomic
    def cancel_schedule(self, request, slug=None):
        post = self.locked_post()
        if post.status != Post.Status.SCHEDULED:
            raise ValidationError("This post is not scheduled.")
        post.scheduled_at, post.scheduled_revision, post.status = None, None, Post.Status.DRAFT
        post.save()
        editorial.audit(request.user, "schedule_cancelled", post)
        return Response(self.get_serializer(post).data)

    @action(detail=True, methods=["post"], permission_classes=[IsAuthenticated, IsReviewer])
    @transaction.atomic
    def feature(self, request, slug=None):
        post = self.locked_post()
        post.is_featured = serializers.BooleanField().run_validation(request.data.get("is_featured"))
        post.save()
        editorial.audit(request.user, "featured_changed", post, is_featured=post.is_featured)
        return Response(self.get_serializer(post).data)

    @action(detail=True, methods=["get"])
    def quality(self, request, slug=None):
        return Response(editorial.quality(self.get_object()))

    @action(detail=True, methods=["post"], url_path="check-links", permission_classes=[IsAuthenticated, IsReviewer])
    def check_links(self, request, slug=None):
        from .link_checks import check_links
        return Response(check_links(self.get_object()))
