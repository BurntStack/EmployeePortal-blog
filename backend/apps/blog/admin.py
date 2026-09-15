from django.contrib import admin

from .models import Category, Post


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ["name", "slug"]
    prepopulated_fields = {"slug": ("name",)}


@admin.register(Post)
class PostAdmin(admin.ModelAdmin):
    list_display = ["title", "category", "author", "status", "is_featured", "published_at"]
    list_filter = ["status", "is_featured", "category"]
    search_fields = ["title", "excerpt", "content"]
    list_editable = ["status", "is_featured"]
    autocomplete_fields = ["author"]
    prepopulated_fields = {"slug": ("title",)}
    date_hierarchy = "published_at"
