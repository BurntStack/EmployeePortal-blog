from django.utils import timezone
from rest_framework import status as http_status
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import Category, Post
from .permissions import IsAdmin, IsOwnerOrAdmin
from .serializers import (
    CategorySerializer,
    PostDetailSerializer,
    PostListSerializer,
    PostWriteSerializer,
)


class CategoryViewSet(viewsets.ReadOnlyModelViewSet):
    """Public, read-only list of blog categories."""

    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    pagination_class = None


class PostViewSet(viewsets.ReadOnlyModelViewSet):
    """Public, read-only access to published blog posts."""

    queryset = Post.objects.filter(status=Post.Status.PUBLISHED).select_related(
        "category", "author"
    )
    lookup_field = "slug"
    filterset_fields = ["category__slug", "is_featured"]
    search_fields = ["title", "excerpt", "content"]
    ordering_fields = ["published_at", "reading_time"]

    def get_serializer_class(self):
        if self.action == "retrieve":
            return PostDetailSerializer
        return PostListSerializer


class EmployeePostViewSet(viewsets.ModelViewSet):
    """
    Authenticated portal endpoint. Employees see and manage only their own
    posts; staff (the admin) see and manage every post. Status only ever
    changes through submit/approve/reject, never a generic update, so an
    employee can't PATCH their own post straight to published.
    """

    serializer_class = PostWriteSerializer
    permission_classes = [IsAuthenticated, IsOwnerOrAdmin]
    lookup_field = "slug"
    filterset_fields = ["status", "category__slug", "author"]
    search_fields = ["title", "excerpt", "content"]
    ordering_fields = ["created_at", "updated_at", "published_at"]

    def get_queryset(self):
        qs = Post.objects.select_related("category", "author")
        if self.request.user.is_staff:
            return qs
        return qs.filter(author=self.request.user)

    def perform_create(self, serializer):
        serializer.save(author=self.request.user)

    def perform_update(self, serializer):
        instance = serializer.instance
        # An employee editing a post that's already pending or published is
        # changing content a reviewer either hasn't seen yet or approved a
        # different version of — send it back to draft so it goes through
        # submit -> approve again rather than silently updating live content.
        # Staff edits (the reviewer's own corrections) are exempt.
        if not self.request.user.is_staff and instance.status != Post.Status.DRAFT:
            serializer.save(status=Post.Status.DRAFT, published_at=None)
        else:
            serializer.save()

    @action(detail=False, methods=["get"], url_path="pending", permission_classes=[IsAuthenticated, IsAdmin])
    def pending(self, request):
        qs = Post.objects.filter(status=Post.Status.PENDING).select_related("category", "author")
        page = self.paginate_queryset(qs)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = self.get_serializer(qs, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=["post"], url_path="submit")
    def submit(self, request, slug=None):
        post = self.get_object()  # scoped to the caller's own posts by get_queryset()
        if post.status != Post.Status.DRAFT:
            return Response({"detail": "Only draft posts can be submitted."}, status=http_status.HTTP_400_BAD_REQUEST)
        post.status = Post.Status.PENDING
        post.save(update_fields=["status", "updated_at"])
        return Response(self.get_serializer(post).data)

    @action(detail=True, methods=["post"], url_path="approve", permission_classes=[IsAuthenticated, IsAdmin])
    def approve(self, request, slug=None):
        post = self.get_object()
        if post.status != Post.Status.PENDING:
            return Response({"detail": "Only pending posts can be approved."}, status=http_status.HTTP_400_BAD_REQUEST)
        post.status = Post.Status.PUBLISHED
        post.published_at = post.published_at or timezone.now()
        post.save(update_fields=["status", "published_at", "updated_at"])
        return Response(self.get_serializer(post).data)

    @action(detail=True, methods=["post"], url_path="reject", permission_classes=[IsAuthenticated, IsAdmin])
    def reject(self, request, slug=None):
        post = self.get_object()
        if post.status != Post.Status.PENDING:
            return Response({"detail": "Only pending posts can be rejected."}, status=http_status.HTTP_400_BAD_REQUEST)
        post.status = Post.Status.DRAFT
        post.save(update_fields=["status", "updated_at"])
        return Response(self.get_serializer(post).data)
