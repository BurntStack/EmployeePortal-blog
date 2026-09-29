from django.contrib import admin

from .models import Category, Post


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ["name", "slug"]
    # Category writes live in the audited portal workflow.
    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(Post)
class PostAdmin(admin.ModelAdmin):
    list_display = ["title", "category", "author", "status", "is_featured", "published_at"]
    list_filter = ["status", "is_featured", "category"]
    search_fields = ["title", "excerpt", "content"]
    # Portal mutations provide revision checks, audit history and notifications.
    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
    autocomplete_fields = ["author"]
    prepopulated_fields = {"slug": ("title",)}
    date_hierarchy = "published_at"
