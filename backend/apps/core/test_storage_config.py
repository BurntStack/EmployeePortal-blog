"""Unit tests for the media storage configuration helpers."""

from django.test import SimpleTestCase

from apps.core.storage_config import is_configured, public_base_url

SUPABASE_ENDPOINT = "https://abcdefghijkl.supabase.co/storage/v1/s3"

FULL_ENV = {
    "AWS_ACCESS_KEY_ID": "key",
    "AWS_SECRET_ACCESS_KEY": "secret",
    "AWS_STORAGE_BUCKET_NAME": "blog-media",
    "AWS_S3_ENDPOINT_URL": SUPABASE_ENDPOINT,
}


class IsConfiguredTests(SimpleTestCase):
    def test_true_when_every_credential_is_present(self):
        self.assertTrue(is_configured(FULL_ENV))

    def test_false_when_any_single_credential_is_missing(self):
        for missing in FULL_ENV:
            env = {k: v for k, v in FULL_ENV.items() if k != missing}
            with self.subTest(missing=missing):
                self.assertFalse(is_configured(env))

    def test_false_for_empty_string_values(self):
        # Vercel returns "" for a variable that exists but was never set;
        # treating that as configured would break the local-disk fallback.
        self.assertFalse(is_configured({**FULL_ENV, "AWS_SECRET_ACCESS_KEY": ""}))

    def test_false_for_an_empty_environment(self):
        self.assertFalse(is_configured({}))


class PublicBaseUrlTests(SimpleTestCase):
    def test_supabase_endpoint_maps_to_the_public_object_path(self):
        # The bug this guards: Supabase's S3 endpoint is not publicly
        # readable, so URLs built against it 400 for anonymous readers -
        # which is every visitor to the public blog.
        self.assertEqual(
            public_base_url(SUPABASE_ENDPOINT, "blog-media"),
            "abcdefghijkl.supabase.co/storage/v1/object/public/blog-media",
        )

    def test_supabase_endpoint_tolerates_a_trailing_slash(self):
        self.assertEqual(
            public_base_url(SUPABASE_ENDPOINT + "/", "blog-media"),
            "abcdefghijkl.supabase.co/storage/v1/object/public/blog-media",
        )

    def test_generic_s3_endpoint_puts_the_bucket_on_the_host(self):
        self.assertEqual(
            public_base_url("https://s3.eu-west-1.amazonaws.com", "blog-media"),
            "s3.eu-west-1.amazonaws.com/blog-media",
        )

    def test_r2_style_endpoint_with_a_path_keeps_the_path(self):
        self.assertEqual(
            public_base_url("https://acct.r2.cloudflarestorage.com/prefix", "blog-media"),
            "acct.r2.cloudflarestorage.com/prefix/blog-media",
        )

    def test_explicit_override_wins(self):
        self.assertEqual(
            public_base_url(SUPABASE_ENDPOINT, "blog-media", override="cdn.burntstack.com"),
            "cdn.burntstack.com",
        )

    def test_override_trailing_slash_is_stripped(self):
        # django-storages joins "<base>/<key>"; a trailing slash here
        # produces a double slash and a 404 on some providers.
        self.assertEqual(
            public_base_url(SUPABASE_ENDPOINT, "b", override="https://cdn.burntstack.com/"),
            "https://cdn.burntstack.com",
        )

    def test_returns_none_when_it_cannot_be_derived(self):
        self.assertIsNone(public_base_url("", "blog-media"))
        self.assertIsNone(public_base_url(SUPABASE_ENDPOINT, ""))
        self.assertIsNone(public_base_url("not-a-url", "blog-media"))
