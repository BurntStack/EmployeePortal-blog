from django.db import models


class TimeStampedModel(models.Model):
    """Abstract base with created/updated timestamps, reused across all apps."""

    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True
        ordering = ["-created_at"]
