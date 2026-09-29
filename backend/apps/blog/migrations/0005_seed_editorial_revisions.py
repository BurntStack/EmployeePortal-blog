from django.db import migrations


def seed(apps, schema_editor):
    Post = apps.get_model("blog", "Post")
    Revision = apps.get_model("blog", "Revision")
    for post in Post.objects.select_related("category").iterator():
        category = post.category
        data = {field: getattr(post, field) for field in ("title", "excerpt", "content", "tags", "reading_time")}
        data["category"] = {"id": category.id, "name": category.name, "slug": category.slug} if category else None
        data["cover_image"] = str(post.cover_image or "")
        revision = Revision.objects.create(post=post, number=1, snapshot=data, created_by_id=post.author_id)
        changes = {}
        if post.status == "published":
            changes["published_revision_id"] = revision.id
        if post.status == "pending":
            changes["submitted_at"] = post.updated_at
        if changes:
            Post.objects.filter(pk=post.id).update(**changes)


class Migration(migrations.Migration):
    dependencies = [("blog", "0004_post_reviewer_post_scheduled_at_post_submitted_at_and_more")]
    operations = [migrations.RunPython(seed, migrations.RunPython.noop)]
