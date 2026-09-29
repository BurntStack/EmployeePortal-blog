from datetime import timedelta
from unittest.mock import patch
from uuid import uuid4

from django.contrib.auth.models import User
from django.core.cache import cache
from django.test import override_settings
from django.utils import timezone
from rest_framework.test import APITestCase

from .editorial import publish_due, send_reminders
from .models import Activity, Category, EditorialSettings, Membership, Notification, Post, ReadEvent, Revision


class EditorialTests(APITestCase):
    def setUp(self):
        cache.clear()
        self.author = User.objects.create_user("author", password="testpass123", email="author@burntstack.com")
        self.other = User.objects.create_user("other", password="testpass123")
        self.admin = User.objects.create_user("admin", is_staff=True)
        self.reviewer = User.objects.create_user("reviewer")
        Membership.objects.create(user=self.reviewer, role="reviewer")
        self.client.force_authenticate(self.author)
        response = self.client.post('/api/portal/blog/', {"title": "Original article", "excerpt": "The original description of this article.", "content": "<p>" + "Useful content. " * 10 + "</p>", "tags": ["engineering"]}, format='json')
        self.assertEqual(response.status_code, 201)
        self.slug = response.data['slug']
        self.url = f'/api/portal/blog/{self.slug}/'

    def act(self, action, user=None, **data):
        self.client.force_authenticate(user or self.admin)
        post = Post.objects.get(slug=self.slug)
        return self.client.post(f'{self.url}{action}/', {"expected_version": post.version, **data}, format='json')

    def live(self):
        self.assertEqual(self.act('submit', self.author).status_code, 200)
        self.assertEqual(self.act('approve').status_code, 200)

    def test_live_snapshot_survives_edits_search_and_category_changes(self):
        cat = Category.objects.create(name="Original category")
        self.client.patch(self.url, {"category_id": cat.id}, format='json')
        self.live()
        self.client.force_authenticate(self.author)
        edit = self.client.patch(self.url, {"title": "Unapproved replacement", "category_id": None, "tags": ["secret"]}, format='json')
        self.assertEqual(edit.status_code, 200)
        detail = self.client.get(f'/api/blog/{self.slug}/').data
        self.assertEqual(detail['title'], 'Original article')
        self.assertEqual(detail['category']['name'], cat.name)
        self.assertEqual(detail['tags'], ['engineering'])
        self.assertEqual(self.client.get('/api/blog/?search=Unapproved').data['count'], 0)
        self.assertEqual(self.client.get('/api/blog/?category__slug=original-category').data['count'], 1)
        self.act('submit', self.author)
        self.act('approve')
        self.assertEqual(self.client.get(f'/api/blog/{self.slug}/').data['title'], 'Unapproved replacement')

    def test_changes_require_reason_and_notify_author(self):
        self.act('submit', self.author)
        self.assertEqual(self.act('request-changes', self.reviewer).status_code, 400)
        response = self.act('request-changes', self.reviewer, body="Please cite the source.")
        self.assertEqual(response.data['status'], 'changes_requested')
        self.client.force_authenticate(self.author)
        self.assertEqual(self.client.get(self.url+'comments/').data[0]['body'], 'Please cite the source.')
        self.assertTrue(Notification.objects.filter(recipient=self.author, message__contains='Changes requested').exists())
        self.assertEqual(self.act('submit', self.author).status_code, 200)

    def test_reviewer_can_publish_but_cannot_manage_users_or_settings(self):
        self.act('submit', self.author)
        self.assertEqual(self.act('approve', self.reviewer).status_code, 200)
        for path in ['people/', 'activity/', 'categories/']:
            self.assertEqual(self.client.get('/api/portal/admin/'+path).status_code, 403)
        self.assertEqual(self.client.patch('/api/portal/admin/settings/', {"review_days": 1}, format='json').status_code, 403)

    def test_contributor_cannot_review_or_read_other_history(self):
        self.act('submit', self.author)
        self.assertEqual(self.act('approve', self.author).status_code, 403)
        self.client.force_authenticate(self.other)
        for path in ['', 'comments/', 'revisions/', 'quality/']:
            self.assertEqual(self.client.get(self.url+path).status_code, 404)
        self.assertEqual(self.act('restore', self.other, revision_id=Revision.objects.first().id).status_code, 404)
        self.assertEqual(self.client.get('/api/portal/admin/analytics/').status_code, 403)

    def test_stale_approval_and_missing_version_are_rejected(self):
        self.client.patch(self.url, {"title": "New version"}, format='json')
        self.act('submit', self.author)
        self.client.force_authenticate(self.admin)
        self.assertEqual(self.client.post(self.url+'approve/', {"expected_version": 1}, format='json').status_code, 409)
        self.assertEqual(self.client.post(self.url+'approve/', {}, format='json').status_code, 400)
        self.assertFalse(Post.objects.get(slug=self.slug).published_revision_id)

    def test_stale_edit_cannot_overwrite_new_work(self):
        self.client.patch(self.url, {"title": "New version", "expected_version": 1}, format='json')
        r = self.client.patch(self.url, {"title": "Stale version", "expected_version": 1}, format='json')
        self.assertEqual(r.status_code, 409)
        self.assertEqual(Post.objects.get(slug=self.slug).title, 'New version')

    def test_schedule_publishes_once_when_due(self):
        self.act('submit', self.author)
        future = timezone.now()+timedelta(hours=1)
        response = self.act('approve', scheduled_at=future.isoformat())
        self.assertEqual(response.data['status'], 'scheduled')
        self.assertEqual(self.client.get('/api/blog/').data['count'], 0)
        self.assertEqual(publish_due(), 0)
        with patch('apps.blog.editorial.timezone.now', return_value=future+timedelta(seconds=1)):
            self.assertEqual(publish_due(), 1)
            self.assertEqual(publish_due(), 0)
        self.assertEqual(self.client.get('/api/blog/').data['count'], 1)
        self.assertEqual(Activity.objects.filter(action='published').count(), 1)

    def test_edit_cancels_scheduled_revision_and_preserves_live_article(self):
        self.live()
        self.client.patch(self.url, {"title": "Second version"}, format='json')
        self.act('submit', self.author)
        self.act('approve', scheduled_at=(timezone.now()+timedelta(hours=1)).isoformat())
        self.client.force_authenticate(self.author)
        self.client.patch(self.url, {"title": "Third version"}, format='json')
        post = Post.objects.get(slug=self.slug)
        self.assertIsNone(post.scheduled_revision_id)
        self.assertIsNone(post.scheduled_at)
        self.assertEqual(self.client.get(f'/api/blog/{self.slug}/').data['title'], 'Original article')

    def test_past_schedule_rolls_back_decision(self):
        self.act('submit', self.author)
        response = self.act('approve', scheduled_at=(timezone.now()-timedelta(hours=1)).isoformat())
        self.assertEqual(response.status_code, 400)
        post = Post.objects.get(slug=self.slug)
        self.assertEqual(post.status, 'pending')
        self.assertEqual(post.comments.count(), 0)

    def test_restore_makes_new_draft_and_retains_live_snapshot(self):
        self.live()
        original = Revision.objects.first()
        self.client.patch(self.url, {"title": "Changed title"}, format='json')
        response = self.act('restore', self.author, revision_id=original.id)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['version'], 3)
        self.assertEqual(response.data['title'], 'Original article')
        self.assertTrue(response.data['is_live'])
        self.assertEqual(Revision.objects.count(), 3)

    def test_assignment_and_daily_reminder_deduplication(self):
        self.act('submit', self.author)
        self.assertEqual(self.act('assign', reviewer_id=self.other.id).status_code, 400)
        self.assertEqual(self.act('assign', reviewer_id=self.reviewer.id).status_code, 200)
        Post.objects.filter(slug=self.slug).update(submitted_at=timezone.now()-timedelta(days=5))
        send_reminders(); send_reminders()
        self.assertEqual(Notification.objects.filter(recipient=self.reviewer, message__contains='overdue').count(), 1)

    def test_user_access_changes_are_audited_and_own_demotion_blocked(self):
        self.client.force_authenticate(self.admin)
        r = self.client.patch(f'/api/portal/admin/people/{self.other.id}/', {"role": "reviewer"}, format='json')
        self.assertEqual(r.status_code, 200, r.data)
        self.assertEqual(r.data['role'], 'reviewer')
        self.assertTrue(Activity.objects.filter(action='access_changed').exists())
        self.assertEqual(self.client.patch(f'/api/portal/admin/people/{self.admin.id}/', {"role": "contributor"}, format='json').status_code, 400)

    def test_primary_and_backup_must_be_distinct_active_admins(self):
        self.client.force_authenticate(self.admin)
        url = '/api/portal/admin/settings/'
        self.assertEqual(self.client.patch(url, {"primary_admin": self.admin.id, "backup_admin": self.admin.id}, format='json').status_code, 400)
        self.assertEqual(self.client.patch(url, {"backup_admin": self.reviewer.id}, format='json').status_code, 400)
        self.assertEqual(self.client.patch(url, {"primary_admin": self.admin.id}, format='json').status_code, 200)

    def test_notifications_are_private_and_mark_read(self):
        self.act('submit', self.author)
        notification = Notification.objects.filter(recipient=self.admin).first()
        self.client.force_authenticate(self.other)
        self.assertEqual(self.client.post(f'/api/portal/admin/notifications/{notification.id}/read/').status_code, 404)
        self.client.force_authenticate(self.admin)
        self.assertEqual(self.client.post(f'/api/portal/admin/notifications/{notification.id}/read/').status_code, 200)
        notification.refresh_from_db()
        self.assertIsNotNone(notification.read_at)

    def test_unpublish_retains_history_and_removes_public_visibility(self):
        self.live()
        self.assertEqual(self.client.delete(self.url).status_code, 400)
        self.assertEqual(self.act('unpublish').status_code, 200)
        self.assertEqual(self.client.get(f'/api/blog/{self.slug}/').status_code, 404)
        self.assertEqual(Revision.objects.count(), 1)
        self.assertTrue(Activity.objects.filter(action='unpublished').exists())

    def test_feature_flag_admin_only(self):
        self.assertEqual(self.act('feature', self.author, is_featured=True).status_code, 403)
        self.assertEqual(self.act('feature', is_featured=True).status_code, 200)
        self.live()
        self.assertEqual(self.client.get('/api/blog/?is_featured=true').data['count'], 1)

    def test_analytics_deduplicates_views_and_counts_engagement(self):
        self.live()
        self.client.force_authenticate(None)
        session = str(uuid4())
        url = f'/api/blog/{self.slug}/events/'
        for engaged in [False, False, True, True]:
            self.assertEqual(self.client.post(url, {"session": session, "engaged": engaged}, format='json').status_code, 202)
        self.assertEqual(ReadEvent.objects.count(), 1)
        self.client.force_authenticate(self.admin)
        response = self.client.get('/api/portal/admin/analytics/')
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data['views'], 1)
        self.assertEqual(response.data['engaged'], 1)
        self.assertEqual(response.data['engagement_rate'], 100)

    def test_draft_cannot_receive_public_events(self):
        self.client.force_authenticate(None)
        self.assertEqual(self.client.post(f'/api/blog/{self.slug}/events/', {"session": str(uuid4())}, format='json').status_code, 404)

    def test_quality_and_overview(self):
        self.client.force_authenticate(self.admin)
        self.assertIn('Add a cover image.', self.client.get(self.url+'quality/').data['issues'])
        response = self.client.get('/api/portal/admin/overview/')
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data['counts']['draft'], 1)
        self.assertEqual(len(response.data['reviewers']), 2)

    def test_category_management_and_used_category_deletion(self):
        self.client.force_authenticate(self.admin)
        response = self.client.post('/api/portal/admin/categories/', {"name": "Cloud"}, format='json')
        self.assertEqual(response.status_code, 201)
        pk = response.data['id']
        self.client.patch(self.url, {"category_id": pk}, format='json')
        self.assertEqual(self.client.delete(f'/api/portal/admin/categories/{pk}/').status_code, 400)
        self.assertEqual(self.client.patch(f'/api/portal/admin/categories/{pk}/', {"name": "Cloud systems"}, format='json').status_code, 200)

    @override_settings(GOOGLE_CLIENT_ID='client', ALLOWED_EMAIL_DOMAIN='burntstack.com', ADMIN_EMAILS=['author@burntstack.com'])
    @patch('apps.core.views.verify_google_token')
    def test_managed_role_survives_login_and_disabled_login_rejected(self, verify):
        verify.return_value = {"email": self.author.email, "hd": "burntstack.com", "email_verified": True}
        self.author.username = self.author.email
        self.author.save()
        Membership.objects.create(user=self.author, role='reviewer')
        self.client.force_authenticate(None)
        response = self.client.post('/api/auth/google/', {"credential": "good"}, format='json')
        self.assertEqual(response.status_code, 200)
        self.author.refresh_from_db()
        self.assertFalse(self.author.is_staff)
        self.author.is_active = False; self.author.save()
        self.assertEqual(self.client.post('/api/auth/google/', {"credential": "good"}, format='json').status_code, 403)

    def test_suspended_user_access_and_refresh_tokens_revoked(self):
        self.client.force_authenticate(None)
        tokens = self.client.post('/api/auth/token/', {"username": "other", "password": "testpass123"}, format='json').data
        self.client.force_authenticate(self.admin)
        self.client.patch(f'/api/portal/admin/people/{self.other.id}/', {"is_active": False}, format='json')
        self.client.force_authenticate(None)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {tokens['access']}")
        self.assertEqual(self.client.get('/api/auth/me/').status_code, 401)
        self.client.credentials()
        self.assertEqual(self.client.post('/api/auth/token/refresh/', {"refresh": tokens['refresh']}, format='json').status_code, 401)


class LinkSafetyTests(APITestCase):
    @patch('apps.blog.link_checks.socket.getaddrinfo', return_value=[(2, 1, 6, '', ('127.0.0.1', 80))])
    @patch('apps.blog.link_checks.http.client.HTTPConnection')
    def test_local_addresses_never_connect(self, connection, lookup):
        from .link_checks import check_url
        result = check_url('http://internal.example/secret')
        self.assertEqual(result['state'], 'unchecked')
        connection.assert_not_called()

    @patch('apps.blog.link_checks.socket.getaddrinfo', return_value=[(2, 1, 6, '', ('8.8.8.8', 80))])
    @patch('apps.blog.link_checks.http.client.HTTPConnection')
    def test_public_404_is_reported_broken_and_connection_pinned(self, connection, lookup):
        from .link_checks import check_url
        connection.return_value.getresponse.return_value.status = 404
        connection.return_value.getresponse.return_value.getheader.return_value = None
        self.assertEqual(check_url('http://example.com/missing')['state'], 'broken')
        self.assertEqual(connection.call_args.args[0], '8.8.8.8')


class SchedulerAuthTests(APITestCase):
    @override_settings(EDITORIAL_CRON_SECRET='')
    def test_unconfigured_scheduler_is_disabled(self):
        self.assertEqual(self.client.get('/api/portal/jobs/').status_code, 403)

    @override_settings(EDITORIAL_CRON_SECRET='test-scheduler-secret')
    def test_scheduler_requires_exact_secret(self):
        self.assertEqual(self.client.get('/api/portal/jobs/').status_code, 403)
        response = self.client.get('/api/portal/jobs/', HTTP_AUTHORIZATION='Bearer test-scheduler-secret')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data, {'published': 0, 'overdue': 0})
