"""
Media storage configuration.

The portal ran on Django's default FileSystemStorage, writing into
BASE_DIR/media. That works on a developer's laptop and cannot work on
Vercel: the deployment filesystem is read-only outside /tmp and is
discarded between invocations, and `config/urls.py` only routes MEDIA_URL
when DEBUG is on - so in production `/media/<anything>` returned 404 and
every uploaded image rendered as a broken <img>, both in the editor and on
the public blog feed (Post.cover_image has the same field type).

The functions here derive an S3-compatible configuration from environment
variables. Supabase Storage is the intended target, but the same settings
work unchanged against Cloudflare R2, Backblaze B2 or AWS S3 - nothing
below is Supabase-specific except `public_base_url`'s default, which
follows Supabase's public-object URL layout.
"""

from urllib.parse import urlsplit

# Supabase serves a public bucket's objects from a different path than the
# one its S3 protocol endpoint uses. django-storages would otherwise build
# URLs against the S3 path, which is not publicly readable.
SUPABASE_S3_SUFFIX = "/storage/v1/s3"
SUPABASE_PUBLIC_TEMPLATE = "{host}/storage/v1/object/public/{bucket}"


def is_configured(env):
    """True when every credential needed for remote storage is present."""
    return all(
        env.get(key)
        for key in (
            "AWS_ACCESS_KEY_ID",
            "AWS_SECRET_ACCESS_KEY",
            "AWS_STORAGE_BUCKET_NAME",
            "AWS_S3_ENDPOINT_URL",
        )
    )


def public_base_url(endpoint_url, bucket, override=None):
    """
    The host+path that stored objects are publicly readable from, which
    django-storages joins the object key onto.

    An explicit AWS_S3_CUSTOM_DOMAIN always wins, so a CDN or a custom
    domain in front of the bucket can be used instead.
    """
    if override:
        return override.strip().rstrip("/")

    if not endpoint_url or not bucket:
        return None

    split = urlsplit(endpoint_url)
    host = split.netloc
    if not host:
        return None

    path = split.path.rstrip("/")
    if path.endswith(SUPABASE_S3_SUFFIX):
        return SUPABASE_PUBLIC_TEMPLATE.format(host=host, bucket=bucket)

    # A generic S3-compatible endpoint: objects live under <host>/<bucket>.
    prefix = f"{host}{path}" if path else host
    return f"{prefix}/{bucket}"
