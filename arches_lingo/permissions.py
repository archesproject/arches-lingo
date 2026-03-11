from django.conf import settings
from rest_framework import permissions

from arches_lingo.const import LINGO_EDITOR_GROUP_NAME


def anonymous_access_allowed():
    """Check if anonymous access is enabled via settings."""
    return getattr(settings, "LINGO_ALLOW_ANONYMOUS_ACCESS", False)


def is_lingo_editor(user):
    """Check if a user is a member of the Lingo Editor group (or is a superuser)."""
    if not user.is_authenticated:
        return False
    if user.is_superuser:
        return True
    return user.groups.filter(name=LINGO_EDITOR_GROUP_NAME).exists()


def is_authenticated_user(user):
    """Check if the request is from a real authenticated user (not anonymous)."""
    return user.is_authenticated and user.username != "anonymous"


class LingoEditor(permissions.BasePermission):
    """DRF permission class requiring membership in the Lingo Editor group."""

    def has_permission(self, request, view):
        return is_lingo_editor(request.user)


class ReadOnlyOrLingoEditor(permissions.BasePermission):
    """Allow read access to anyone (or authenticated users only), require Lingo Editor for writes."""

    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            if anonymous_access_allowed():
                return True
            return is_authenticated_user(request.user)
        return is_lingo_editor(request.user)
