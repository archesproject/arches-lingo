from rest_framework import permissions

LINGO_EDITOR_GROUP_NAME = "Lingo Editor"


def is_lingo_editor(user):
    """Check if a user is a member of the Lingo Editor group (or is a superuser)."""
    if not user.is_authenticated:
        return False
    if user.is_superuser:
        return True
    return user.groups.filter(name=LINGO_EDITOR_GROUP_NAME).exists()


class LingoEditor(permissions.BasePermission):
    """DRF permission class requiring membership in the Lingo Editor group."""

    def has_permission(self, request, view):
        return is_lingo_editor(request.user)


class ReadOnlyOrLingoEditor(permissions.BasePermission):
    """Allow read access to anyone, but require Lingo Editor for writes."""

    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return True
        return is_lingo_editor(request.user)
