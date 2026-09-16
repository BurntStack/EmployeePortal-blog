import io

from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from .models import Category, Post
from .sanitize import clean_post_html, visible_text_length


def make_user(username, is_staff=False):
    return User.objects.create_user(
        username=username,
        password="TestPass123!",
        first_name=username.split(".")[0].title(),
        last_name="Doe",
        is_staff=is_staff,
    )


class PostWorkflowTests(APITestCase):
    """
    The employee-facing write API and its approval workflow. These pin down
    exactly the boundaries hand-verified with curl during development: an
    employee only ever sees their own posts, status only moves through the
    dedicated actions, and only staff can approve/reject.
    """

    def setUp(self):
        self.category = Category.objects.create(name="Engineering")
        self.employee = make_user("alice.employee")
        self.other_employee = make_user("bob.employee")
        self.admin = make_user("carol.admin", is_staff=True)
        self.portal_list_url = reverse("employee-post-list")

    def auth(self, user):
        self.client.force_authenticate(user=user)

    def create_post(self, user, **overrides):
        payload = {
            "title": "A Test Post Title",
            "excerpt": "A sufficiently long excerpt for validation purposes.",
            "content": "A" * 60,
            "reading_time": 5,
        }
        payload.update(overrides)
        self.auth(user)
        response = self.client.post(self.portal_list_url, payload, format="json")
        return response

    # --- creation & ownership -------------------------------------------------

    def test_unauthenticated_create_is_rejected(self):
        response = self.client.post(self.portal_list_url, {"title": "x"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_employee_can_create_draft_and_is_set_as_author(self):
        response = self.create_post(self.employee)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        post = Post.objects.get(slug=response.data["slug"])
        self.assertEqual(post.author, self.employee)
        self.assertEqual(post.status, Post.Status.DRAFT)

    def test_status_is_not_writable_on_create_or_update(self):
        # Even if an employee sends status=published directly, it must be ignored.
        response = self.create_post(self.employee, status="published")
        self.assertEqual(response.data["status"], Post.Status.DRAFT)

        slug = response.data["slug"]
        detail_url = reverse("employee-post-detail", args=[slug])
        patch = self.client.patch(detail_url, {"status": "published"}, format="json")
        self.assertEqual(patch.status_code, status.HTTP_200_OK)
        self.assertEqual(Post.objects.get(slug=slug).status, Post.Status.DRAFT)

    def test_employee_cannot_see_or_edit_another_employees_post(self):
        mine = self.create_post(self.employee).data
        self.auth(self.other_employee)

        detail_url = reverse("employee-post-detail", args=[mine["slug"]])
        get_response = self.client.get(detail_url)
        patch_response = self.client.patch(detail_url, {"title": "Hijacked"}, format="json")
        list_response = self.client.get(self.portal_list_url)

        self.assertEqual(get_response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(patch_response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual([p["slug"] for p in list_response.data["results"]], [])

    def test_admin_sees_every_employees_posts(self):
        self.create_post(self.employee)
        self.create_post(self.other_employee)
        self.auth(self.admin)
        response = self.client.get(self.portal_list_url)
        self.assertEqual(response.data["count"], 2)

    # --- submit / approve / reject --------------------------------------------

    def submit(self, user, slug):
        self.auth(user)
        return self.client.post(reverse("employee-post-submit", args=[slug]))

    def approve(self, user, slug):
        self.auth(user)
        return self.client.post(reverse("employee-post-approve", args=[slug]))

    def reject(self, user, slug):
        self.auth(user)
        return self.client.post(reverse("employee-post-reject", args=[slug]))

    def test_full_approval_workflow_and_public_visibility(self):
        slug = self.create_post(self.employee).data["slug"]
        public_url = reverse("post-list")

        # Draft: invisible publicly.
        self.assertEqual([p["slug"] for p in self.client.get(public_url).data["results"]], [])

        # Submit: draft -> pending.
        submit_response = self.submit(self.employee, slug)
        self.assertEqual(submit_response.status_code, status.HTTP_200_OK)
        self.assertEqual(submit_response.data["status"], Post.Status.PENDING)
        self.assertEqual([p["slug"] for p in self.client.get(public_url).data["results"]], [])

        # A non-staff user, including the author, cannot approve.
        forbidden = self.approve(self.employee, slug)
        self.assertEqual(forbidden.status_code, status.HTTP_403_FORBIDDEN)

        # Admin approves: pending -> published, stamps published_at.
        approve_response = self.approve(self.admin, slug)
        self.assertEqual(approve_response.status_code, status.HTTP_200_OK)
        self.assertEqual(approve_response.data["status"], Post.Status.PUBLISHED)
        self.assertIsNotNone(approve_response.data["published_at"])

        # Now it's on the public feed.
        public_slugs = [p["slug"] for p in self.client.get(public_url).data["results"]]
        self.assertEqual(public_slugs, [slug])

    def test_cannot_submit_a_post_that_is_not_a_draft(self):
        slug = self.create_post(self.employee).data["slug"]
        self.submit(self.employee, slug)  # now pending
        second_submit = self.submit(self.employee, slug)
        self.assertEqual(second_submit.status_code, status.HTTP_400_BAD_REQUEST)

    def test_cannot_approve_a_post_that_is_not_pending(self):
        slug = self.create_post(self.employee).data["slug"]  # still draft
        response = self.approve(self.admin, slug)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_reject_sends_a_pending_post_back_to_draft(self):
        slug = self.create_post(self.employee).data["slug"]
        self.submit(self.employee, slug)
        response = self.reject(self.admin, slug)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["status"], Post.Status.DRAFT)

    def test_non_staff_cannot_reject(self):
        slug = self.create_post(self.employee).data["slug"]
        self.submit(self.employee, slug)
        response = self.reject(self.other_employee, slug)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_editing_a_published_post_sends_it_back_to_draft(self):
        # Found in security review: an author editing a live, already-approved
        # post must not silently change what's public — it has to go through
        # submit -> approve again, not just update in place.
        slug = self.create_post(self.employee).data["slug"]
        self.submit(self.employee, slug)
        self.approve(self.admin, slug)

        public_before = self.client.get(reverse("post-detail", args=[slug])).data["title"]
        self.assertEqual(public_before, "A Test Post Title")

        self.auth(self.employee)
        detail_url = reverse("employee-post-detail", args=[slug])
        patch = self.client.patch(detail_url, {"title": "Edited After Approval"}, format="json")
        self.assertEqual(patch.status_code, status.HTTP_200_OK)
        self.assertEqual(patch.data["status"], Post.Status.DRAFT)
        self.assertIsNone(patch.data["published_at"])

        # The edit is not live — the post dropped off the public feed entirely.
        public_response = self.client.get(reverse("post-detail", args=[slug]))
        self.assertEqual(public_response.status_code, status.HTTP_404_NOT_FOUND)

    def test_staff_editing_a_published_post_keeps_it_published(self):
        # A reviewer fixing a typo on an already-approved post shouldn't have
        # to re-approve their own edit.
        slug = self.create_post(self.employee).data["slug"]
        self.submit(self.employee, slug)
        self.approve(self.admin, slug)

        self.auth(self.admin)
        detail_url = reverse("employee-post-detail", args=[slug])
        patch = self.client.patch(detail_url, {"title": "Typo Fixed"}, format="json")
        self.assertEqual(patch.data["status"], Post.Status.PUBLISHED)

    def test_pending_queue_is_admin_only_and_lists_everyones_submissions(self):
        slug1 = self.create_post(self.employee).data["slug"]
        slug2 = self.create_post(self.other_employee).data["slug"]
        self.submit(self.employee, slug1)
        self.submit(self.other_employee, slug2)

        pending_url = reverse("employee-post-pending")

        self.auth(self.employee)
        forbidden = self.client.get(pending_url)
        self.assertEqual(forbidden.status_code, status.HTTP_403_FORBIDDEN)

        self.auth(self.admin)
        response = self.client.get(pending_url)
        self.assertEqual(response.data["count"], 2)


class SlugGenerationTests(APITestCase):
    def test_duplicate_titles_get_distinct_slugs(self):
        author = make_user("frank.writer")
        first = Post.objects.create(title="Launch Update", excerpt="e" * 20, content="c" * 60, author=author)
        second = Post.objects.create(title="Launch Update", excerpt="e" * 20, content="c" * 60, author=author)
        third = Post.objects.create(title="Launch Update", excerpt="e" * 20, content="c" * 60, author=author)
        self.assertEqual([first.slug, second.slug, third.slug], ["launch-update", "launch-update-2", "launch-update-3"])


class PublicFeedTests(APITestCase):
    """The read-only public endpoint burntstack.com/blog consumes."""

    def setUp(self):
        self.category = Category.objects.create(name="AI")
        self.author = make_user("dana.writer")

    def test_only_published_posts_are_listed(self):
        Post.objects.create(
            title="Draft Post", excerpt="e" * 20, content="c" * 60,
            author=self.author, status=Post.Status.DRAFT,
        )
        published = Post.objects.create(
            title="Published Post", excerpt="e" * 20, content="c" * 60,
            author=self.author, status=Post.Status.PUBLISHED, category=self.category,
        )
        response = self.client.get(reverse("post-list"))
        slugs = [p["slug"] for p in response.data["results"]]
        self.assertEqual(slugs, [published.slug])

    def test_detail_view_includes_author_display_name_and_category(self):
        post = Post.objects.create(
            title="Published Post", excerpt="e" * 20, content="c" * 60,
            author=self.author, status=Post.Status.PUBLISHED, category=self.category,
        )
        response = self.client.get(reverse("post-detail", args=[post.slug]))
        self.assertEqual(response.data["author"], "Dana Doe")
        self.assertEqual(response.data["category"]["name"], "AI")


class MeEndpointTests(APITestCase):
    def test_requires_authentication(self):
        response = self.client.get(reverse("me"))
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_reports_staff_flag_correctly(self):
        admin = make_user("erin.admin", is_staff=True)
        self.client.force_authenticate(user=admin)
        response = self.client.get(reverse("me"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data["is_staff"])
        self.assertEqual(response.data["username"], "erin.admin")


class ContentSanitizationTests(APITestCase):
    """
    `content` is real HTML from the rich text editor now, not markdown text —
    it goes through admin approval, but that's not a substitute for treating
    it as untrusted input on the way in.
    """

    def test_script_tags_are_stripped(self):
        cleaned = clean_post_html("<p>Hello</p><script>alert('x')</script>")
        self.assertNotIn("<script", cleaned)
        self.assertIn("Hello", cleaned)

    def test_disallowed_attributes_are_stripped(self):
        cleaned = clean_post_html('<p onclick="alert(1)" style="color:red">Hi</p>')
        self.assertNotIn("onclick", cleaned)
        self.assertNotIn("style", cleaned)

    def test_allowed_formatting_survives(self):
        html = "<h2>Title</h2><p><strong>Bold</strong> and <em>italic</em>.</p><img src='/x.png' alt='x'>"
        cleaned = clean_post_html(html)
        self.assertIn("<h2>", cleaned)
        self.assertIn("<strong>", cleaned)
        self.assertIn("<img", cleaned)

    def test_tables_survive_sanitization(self):
        html = "<table><thead><tr><th>Plan</th></tr></thead><tbody><tr><td>Starter</td></tr></tbody></table>"
        cleaned = clean_post_html(html)
        self.assertIn("<table>", cleaned)
        self.assertIn("<td>Starter</td>", cleaned)

    def test_visible_text_length_ignores_markup(self):
        html = "<p>" + ("a" * 60) + "</p>"
        self.assertEqual(visible_text_length(html), 60)

    def test_post_creation_rejects_content_thats_only_markup(self):
        user = make_user("frank.employee")
        self.client.force_authenticate(user=user)
        payload = {
            "title": "A Test Post Title",
            "excerpt": "A sufficiently long excerpt for validation purposes.",
            "content": "<p></p>" * 20,  # lots of markup, no real text
            "reading_time": 5,
        }
        response = self.client.post(reverse("employee-post-list"), payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_post_creation_strips_script_tags_from_stored_content(self):
        user = make_user("grace.employee")
        self.client.force_authenticate(user=user)
        payload = {
            "title": "A Test Post Title",
            "excerpt": "A sufficiently long excerpt for validation purposes.",
            "content": "<p>" + ("a" * 60) + "</p><script>alert(1)</script>",
            "reading_time": 5,
        }
        response = self.client.post(reverse("employee-post-list"), payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        post = Post.objects.get(slug=response.data["slug"])
        self.assertNotIn("<script", post.content)


def make_test_image(name="test.png"):
    from PIL import Image

    buf = io.BytesIO()
    Image.new("RGB", (2, 2), color="red").save(buf, format="PNG")
    buf.seek(0)
    return SimpleUploadedFile(name, buf.read(), content_type="image/png")


class ContentImageUploadTests(APITestCase):
    """The rich text editor's image button / drag-drop / paste all hit this."""

    def setUp(self):
        self.user = make_user("henry.employee")
        self.url = reverse("content-image-upload")

    def test_unauthenticated_upload_is_rejected(self):
        response = self.client.post(self.url, {"image": make_test_image()}, format="multipart")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_authenticated_upload_returns_a_url(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.post(self.url, {"image": make_test_image()}, format="multipart")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(response.data["url"].startswith("http"))
        self.assertIn("blog-content/", response.data["url"])

    def test_missing_file_is_rejected(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.post(self.url, {}, format="multipart")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_non_image_content_type_is_rejected(self):
        self.client.force_authenticate(user=self.user)
        bad_file = SimpleUploadedFile("notes.txt", b"just text", content_type="text/plain")
        response = self.client.post(self.url, {"image": bad_file}, format="multipart")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_oversized_file_is_rejected(self):
        self.client.force_authenticate(user=self.user)
        huge = SimpleUploadedFile("big.png", b"0" * (8 * 1024 * 1024 + 1), content_type="image/png")
        response = self.client.post(self.url, {"image": huge}, format="multipart")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
