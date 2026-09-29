"""Editorial state transitions. Call mutations inside a transaction with the post locked."""
from datetime import timedelta
from html.parser import HTMLParser
from urllib.parse import urlparse

from django.contrib.auth.models import User
from django.db import transaction
from django.utils import timezone

from .models import Activity, EditorialSettings, Notification, Post, Revision
from .sanitize import clean_post_html

CONTENT_FIELDS = ("title", "excerpt", "content", "tags", "reading_time")


def snapshot(post):
    data = {field: getattr(post, field) for field in CONTENT_FIELDS}
    data["content"] = clean_post_html(data["content"])
    data["category"] = ({"id": post.category_id, "name": post.category.name, "slug": post.category.slug} if post.category_id else None)
    data["cover_image"] = post.cover_image.name if post.cover_image else ""
    return data


def save_revision(post, actor):
    return Revision.objects.create(post=post, number=post.version, snapshot=snapshot(post), created_by=actor)


def audit(actor, action, post=None, target="", **details):
    return Activity.objects.create(actor=actor, actor_name=(actor.get_full_name() or actor.username) if actor else "Scheduler", action=action, post=post, target=target or (post.title if post else ""), details=details)


def notify(users, post, message, key=None):
    for user_id in set(users):
        if user_id and User.objects.filter(pk=user_id, is_active=True).exists():
            values = dict(recipient_id=user_id, post=post, message=message[:500])
            if key:
                Notification.objects.get_or_create(dedupe_key=f"{key}:{user_id}", defaults=values)
            else:
                Notification.objects.create(**values)


def reviewers():
    from .permissions import can_review
    return [user.id for user in User.objects.filter(is_active=True).select_related("portal_membership") if can_review(user)]


def publish(post, revision, actor=None):
    post.published_revision = revision
    post.published_at = post.published_at or timezone.now()
    post.scheduled_at = None
    post.scheduled_revision = None
    post.status = Post.Status.PUBLISHED
    post.save()
    audit(actor, "published", post, revision=revision.number)
    notify([post.author_id], post, f'Published: {post.title}')


def publish_due():
    ids = Post.objects.filter(status=Post.Status.SCHEDULED, scheduled_at__lte=timezone.now()).values_list("id", flat=True)
    count = 0
    for pk in list(ids):
        with transaction.atomic():
            post = Post.objects.select_for_update().get(pk=pk)
            if post.status == Post.Status.SCHEDULED and post.scheduled_at and post.scheduled_at <= timezone.now() and post.scheduled_revision_id:
                publish(post, post.scheduled_revision)
                count += 1
    return count


def send_reminders():
    settings, _ = EditorialSettings.objects.get_or_create(pk=1)
    cutoff = timezone.now() - timedelta(days=settings.review_days)
    posts = Post.objects.filter(status=Post.Status.PENDING, submitted_at__lte=cutoff)
    count = 0
    for post in posts:
        recipients = [post.reviewer_id] if post.reviewer_id else reviewers()
        recipients += [settings.primary_admin_id, settings.backup_admin_id]
        notify(recipients, post, f'Review overdue: {post.title}', key=f"overdue:{post.id}:{post.version}:{timezone.localdate()}")
        count += 1
    return count


class ContentLinks(HTMLParser):
    def __init__(self, content):
        super().__init__()
        self.links, self.ids, self.missing_alt = [], set(), 0
        self.feed(content)

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if "id" in attrs:
            self.ids.add(attrs["id"])
        if tag == "a":
            self.links.append(attrs.get("href", ""))
        if tag == "img" and not attrs.get("alt", "").strip():
            self.missing_alt += 1


def quality(post):
    issues = []
    if not post.cover_image:
        issues.append("Add a cover image.")
    if not post.category_id:
        issues.append("Choose a category.")
    if not post.tags:
        issues.append("Add topic tags.")
    if not post.excerpt.strip():
        issues.append("Add a search and social description (excerpt).")
    parsed = ContentLinks(post.content)
    if parsed.missing_alt:
        issues.append(f"Add descriptive alt text to {parsed.missing_alt} image(s).")
    for link in parsed.links:
        url = urlparse(link)
        if not link or (url.scheme and url.scheme not in ("https", "http", "mailto")) or (url.scheme in ("http", "https") and not url.hostname):
            issues.append(f"Invalid link: {link or '(empty)'}")
        elif link.startswith("#") and link[1:] not in parsed.ids:
            issues.append(f"Missing anchor: {link}")
        elif url.path.startswith("/blog/") and not url.netloc:
            slug = url.path.strip("/").split("/")[-1]
            if not Post.objects.filter(slug=slug, published_revision__isnull=False).exists():
                issues.append(f"Unpublished or missing internal article: {link}")
    return {"issues": issues, "links": list(dict.fromkeys(parsed.links)), "external_links_checked": False}
