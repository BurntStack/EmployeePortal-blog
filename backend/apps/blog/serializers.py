from django.core.files.storage import default_storage
from rest_framework import serializers

from .models import Category, Post
from .sanitize import clean_post_html, visible_text_length


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ["id", "name", "slug"]


def _author_name(post):
    return post.author.get_full_name() or post.author.username


def public_data(post, context, detail=False):
    # Public reads always use the approved snapshot, never the working copy.
    from .editorial import snapshot
    data = dict(post.published_revision.snapshot) if post.published_revision_id else snapshot(post)
    if "content" in data:
        data["content"] = clean_post_html(data["content"])
    request = context.get("request")
    cover = data.get("cover_image")
    if cover:
        cover = default_storage.url(cover)
        if request:
            cover = request.build_absolute_uri(cover)
    data.update(id=post.id, slug=post.slug, author=_author_name(post), cover_image=cover or None,
                is_featured=post.is_featured, published_at=post.published_at, created_at=post.created_at)
    if not detail:
        data.pop("content", None)
        data.pop("created_at", None)
        data["category"] = data["category"]["name"] if data.get("category") else None
    return data


class PostListSerializer(serializers.BaseSerializer):
    def to_representation(self, instance):
        return public_data(instance, self.context)


class PostDetailSerializer(serializers.BaseSerializer):
    def to_representation(self, instance):
        data = public_data(instance, self.context, detail=True)
        category = data.get("category")
        posts = Post.objects.none()
        if category:
            posts = Post.objects.filter(published_revision__isnull=False, published_revision__snapshot__category__id=category["id"]).exclude(pk=instance.pk).select_related("published_revision", "author")[:3]
        data["related_posts"] = PostListSerializer(posts, many=True, context=self.context).data
        return data


class PostWriteSerializer(serializers.ModelSerializer):
    category = serializers.StringRelatedField(read_only=True)
    category_id = serializers.PrimaryKeyRelatedField(source="category", queryset=Category.objects.all(), required=False, allow_null=True)
    author = serializers.SerializerMethodField()
    author_id = serializers.IntegerField(read_only=True)
    reviewer_name = serializers.SerializerMethodField()
    is_live = serializers.SerializerMethodField()
    expected_version = serializers.IntegerField(write_only=True, required=False)

    class Meta:
        model = Post
        fields = ["id", "title", "slug", "excerpt", "content", "category", "category_id", "author", "author_id",
                  "cover_image", "tags", "reading_time", "status", "published_at", "created_at", "updated_at",
                  "is_featured", "reviewer", "reviewer_name", "version", "expected_version", "is_live", "scheduled_at", "submitted_at"]
        read_only_fields = ["id", "slug", "status", "published_at", "created_at", "updated_at", "is_featured", "reviewer", "version", "scheduled_at", "submitted_at"]

    def get_author(self, obj):
        return _author_name(obj)

    def get_reviewer_name(self, obj):
        return (obj.reviewer.get_full_name() or obj.reviewer.username) if obj.reviewer_id else None

    def get_is_live(self, obj):
        return bool(obj.published_revision_id)

    def validate_title(self, value):
        if len(value.strip()) < 4:
            raise serializers.ValidationError("Title must be at least 4 characters.")
        return value.strip()

    def validate_excerpt(self, value):
        if len(value.strip()) < 10:
            raise serializers.ValidationError("Excerpt must be at least 10 characters.")
        return value.strip()

    def validate_tags(self, value):
        if not isinstance(value, list) or len(value) > 20 or any(not isinstance(t, str) or len(t) > 60 for t in value):
            raise serializers.ValidationError("Use up to 20 tags, each at most 60 characters.")
        return list(dict.fromkeys(t.strip() for t in value if t.strip()))

    def validate_reading_time(self, value):
        if not 1 <= value <= 240:
            raise serializers.ValidationError("Reading time must be between 1 and 240 minutes.")
        return value

    def validate_content(self, value):
        cleaned = clean_post_html(value.strip())
        if visible_text_length(cleaned) < 50:
            raise serializers.ValidationError("Content must be at least 50 characters.")
        return cleaned
