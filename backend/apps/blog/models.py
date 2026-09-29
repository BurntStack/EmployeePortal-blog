from django.conf import settings
from django.db import models
from django.utils import timezone
from django.utils.text import slugify

from apps.core.models import TimeStampedModel


class Category(TimeStampedModel):
    name = models.CharField(max_length=80, unique=True)
    slug = models.SlugField(max_length=90, unique=True, blank=True)

    class Meta:
        ordering = ["name"]
        verbose_name_plural = "Categories"

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class Post(TimeStampedModel):
    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        PENDING = "pending", "Pending review"
        PUBLISHED = "published", "Published"
        CHANGES_REQUESTED = "changes_requested", "Changes requested"
        REJECTED = "rejected", "Rejected"
        SCHEDULED = "scheduled", "Scheduled"
        ARCHIVED = "archived", "Archived"

    title = models.CharField(max_length=200)
    slug = models.SlugField(max_length=220, unique=True, blank=True)
    excerpt = models.TextField(max_length=400)
    content = models.TextField()
    category = models.ForeignKey(
        Category, on_delete=models.SET_NULL, null=True, related_name="posts"
    )
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="posts"
    )
    cover_image = models.ImageField(upload_to="blog/", blank=True, null=True)
    tags = models.JSONField(default=list, blank=True)
    reading_time = models.PositiveIntegerField(default=5, help_text="Minutes")
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.DRAFT, db_index=True
    )
    is_featured = models.BooleanField(default=False)
    published_at = models.DateTimeField(blank=True, null=True)

    published_revision = models.ForeignKey("Revision", null=True, blank=True, on_delete=models.SET_NULL, related_name="live_posts")
    scheduled_revision = models.ForeignKey("Revision", null=True, blank=True, on_delete=models.SET_NULL, related_name="scheduled_posts")
    scheduled_at = models.DateTimeField(null=True, blank=True, db_index=True)
    submitted_at = models.DateTimeField(null=True, blank=True)
    reviewer = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="assigned_posts")
    version = models.PositiveIntegerField(default=1)

    class Meta(TimeStampedModel.Meta):
        ordering = ["-published_at", "-created_at"]
        indexes = [
            models.Index(fields=["status", "-published_at"], name="post_pub_status_date_idx"),
            models.Index(fields=["category", "status", "-published_at"], name="post_cat_status_date_idx"),
        ]

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = self._unique_slug()
        if self.status == self.Status.PUBLISHED and not self.published_at:
            self.published_at = timezone.now()
        super().save(*args, **kwargs)

    def _unique_slug(self):
        base = slugify(self.title)[:210] or "post"
        slug = base
        suffix = 2
        while Post.objects.filter(slug=slug).exclude(pk=self.pk).exists():
            slug = f"{base}-{suffix}"
            suffix += 1
        return slug

    def __str__(self):
        return self.title


class Membership(models.Model):
    class Role(models.TextChoices):
        CONTRIBUTOR = "contributor", "Contributor"
        REVIEWER = "reviewer", "Reviewer"
        ADMIN = "admin", "Administrator"

    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="portal_membership")
    role = models.CharField(max_length=20, choices=Role.choices, default=Role.CONTRIBUTOR)


class Revision(models.Model):
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name="revisions")
    number = models.PositiveIntegerField()
    snapshot = models.JSONField()
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-number"]
        constraints = [models.UniqueConstraint(fields=["post", "number"], name="unique_post_revision")]


class ReviewComment(models.Model):
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name="comments")
    author = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL)
    body = models.TextField(max_length=4000)
    decision = models.CharField(max_length=30, default="comment")
    version = models.PositiveIntegerField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at", "id"]


class Activity(models.Model):
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL)
    actor_name = models.CharField(max_length=254)
    action = models.CharField(max_length=50)
    post = models.ForeignKey(Post, null=True, on_delete=models.SET_NULL)
    target = models.CharField(max_length=254)
    details = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["-created_at", "-id"]


class Notification(models.Model):
    recipient = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    post = models.ForeignKey(Post, null=True, on_delete=models.SET_NULL)
    message = models.CharField(max_length=500)
    read_at = models.DateTimeField(null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    dedupe_key = models.CharField(max_length=150, null=True, unique=True)

    class Meta:
        ordering = ["-created_at", "-id"]


class EditorialSettings(models.Model):
    primary_admin = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="primary_editorial_roles")
    backup_admin = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="backup_editorial_roles")
    review_days = models.PositiveSmallIntegerField(default=3)
    guidelines = models.TextField(default="Check accuracy, sources, clarity, accessibility, and confidential information. Give specific, constructive feedback. Apply the same standards to every author. Escalate claims outside your expertise. The backup handles reviews when the primary admin is unavailable.")


class ReadEvent(models.Model):
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name="read_events")
    # Random browser-session ID; no IP address, cookie, or personal data stored.
    session = models.UUIDField()
    day = models.DateField()
    engaged = models.BooleanField(default=False)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["post", "session", "day"], name="unique_daily_read")]
