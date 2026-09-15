from rest_framework import serializers

from .models import Category, Post


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ["id", "name", "slug"]


def _author_name(post):
    name = post.author.get_full_name()
    return name or post.author.username


class PostListSerializer(serializers.ModelSerializer):
    category = serializers.StringRelatedField()
    author = serializers.SerializerMethodField()

    class Meta:
        model = Post
        fields = [
            "id", "title", "slug", "excerpt", "category", "author",
            "cover_image", "tags", "reading_time", "is_featured", "published_at",
        ]

    def get_author(self, obj):
        return _author_name(obj)


class PostDetailSerializer(serializers.ModelSerializer):
    category = CategorySerializer(read_only=True)
    author = serializers.SerializerMethodField()

    class Meta:
        model = Post
        fields = [
            "id", "title", "slug", "excerpt", "content", "category", "author",
            "cover_image", "tags", "reading_time", "is_featured", "published_at",
            "created_at",
        ]

    def get_author(self, obj):
        return _author_name(obj)


class PostWriteSerializer(serializers.ModelSerializer):
    """
    Employee-facing create/update serializer. `status`, `is_featured` and
    `published_at` are deliberately absent — status only moves through the
    submit/approve/reject actions, and `is_featured` is admin-only, set via
    Django admin or the review screen, never by the post's own author.
    """

    category = serializers.StringRelatedField(read_only=True)
    category_id = serializers.PrimaryKeyRelatedField(
        source="category", queryset=Category.objects.all(),
        required=False, allow_null=True, write_only=True,
    )
    author = serializers.SerializerMethodField()
    status = serializers.CharField(read_only=True)

    class Meta:
        model = Post
        fields = [
            "id", "title", "slug", "excerpt", "content", "category", "category_id", "author",
            "cover_image", "tags", "reading_time", "status", "published_at", "created_at",
        ]
        read_only_fields = ["id", "slug", "published_at", "created_at"]

    def get_author(self, obj):
        return _author_name(obj)

    def validate_title(self, value):
        if len(value.strip()) < 4:
            raise serializers.ValidationError("Title must be at least 4 characters.")
        return value.strip()

    def validate_excerpt(self, value):
        if len(value.strip()) < 10:
            raise serializers.ValidationError("Excerpt must be at least 10 characters.")
        return value.strip()

    def validate_content(self, value):
        if len(value.strip()) < 50:
            raise serializers.ValidationError("Content must be at least 50 characters.")
        return value.strip()
