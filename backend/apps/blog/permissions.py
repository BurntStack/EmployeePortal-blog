from rest_framework.permissions import BasePermission


class IsOwnerOrAdmin(BasePermission):
    """
    Employees may only read/write their own posts. Staff (the admin) can
    read/write every post, including the approve/reject actions.
    """

    def has_object_permission(self, request, view, obj):
        return request.user.is_staff or obj.author_id == request.user.id


class IsAdmin(BasePermission):
    """Staff-only actions (approve/reject/pending review queue)."""

    def has_permission(self, request, view):
        return bool(request.user and request.user.is_staff)
