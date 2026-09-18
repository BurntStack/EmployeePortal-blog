from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("blog", "0002_remove_post_is_published_post_status_and_more")]

    operations = [
        migrations.AddIndex(
            model_name="post",
            index=models.Index(
                fields=["status", "-published_at"],
                name="post_pub_status_date_idx",
            ),
        ),
        migrations.AddIndex(
            model_name="post",
            index=models.Index(
                fields=["category", "status", "-published_at"],
                name="post_cat_status_date_idx",
            ),
        ),
    ]
