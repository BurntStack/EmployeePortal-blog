from rest_framework.permissions import BasePermission
from .models import Membership


def role_for(user):
    if not user or not user.is_authenticated or not user.is_active:
        return None
    if user.is_superuser:
        return "admin"
    try:
        return user.portal_membership.role
    except Membership.DoesNotExist:
        return "admin" if user.is_staff else "contributor"


def can_review(user):
    return role_for(user) in ("admin", "reviewer")


class IsOwnerOrAdmin(BasePermission):
    def has_object_permission(self, request, view, obj):
        return can_review(request.user) or obj.author_id == request.user.id


class IsAdmin(BasePermission):
    def has_permission(self, request, view):
        return role_for(request.user) == "admin"


class IsReviewer(BasePermission):
    def has_permission(self, request, view):
        return can_review(request.user)
