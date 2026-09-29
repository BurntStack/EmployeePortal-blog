from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.test import TransactionTestCase


class EditorialSnapshotMigrationTests(TransactionTestCase):
    def test_existing_published_and_pending_posts_keep_their_content(self):
        old = [('blog', '0003_post_public_read_indexes')]
        new = [('blog', '0005_seed_editorial_revisions')]
        executor = MigrationExecutor(connection)
        executor.migrate(old)
        try:
            apps = executor.loader.project_state(old).apps
            User = apps.get_model('auth', 'User')
            Post = apps.get_model('blog', 'Post')
            Category = apps.get_model('blog', 'Category')
            user = User.objects.create(username='migration-author')
            category = Category.objects.create(name='Engineering', slug='engineering')
            live = Post.objects.create(title='Existing live article', slug='existing-live', excerpt='A live article.', content='<p>Original body</p>', status='published', author=user, category=category, cover_image='blog/cover.png')
            pending = Post.objects.create(title='Awaiting review', slug='awaiting-review', excerpt='A pending article.', content='<p>Pending body</p>', status='pending', author=user)
            executor = MigrationExecutor(connection)
            executor.migrate(new)
            apps = executor.loader.project_state(new).apps
            Post = apps.get_model('blog', 'Post')
            live = Post.objects.get(pk=live.pk)
            self.assertIsNotNone(live.published_revision_id)
            self.assertEqual(live.published_revision.snapshot['content'], '<p>Original body</p>')
            self.assertEqual(live.published_revision.snapshot['cover_image'], 'blog/cover.png')
            self.assertEqual(live.published_revision.snapshot['category']['slug'], 'engineering')
            pending = Post.objects.get(pk=pending.pk)
            self.assertIsNone(pending.published_revision_id)
            self.assertIsNotNone(pending.submitted_at)
            self.assertEqual(pending.revisions.count(), 1)
        finally:
            MigrationExecutor(connection).migrate(new)
