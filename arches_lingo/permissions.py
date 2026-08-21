from django.conf import settings
from rest_framework import permissions

from arches_lingo.const import (
    LINGO_ADMIN_GROUP_NAME,
    LINGO_EDITOR_GROUP_NAME,
    LINGO_EXPORTER_GROUP_NAME,
)


def anonymous_access_allowed():
    """Check if anonymous access is enabled via settings."""
    return getattr(settings, "LINGO_ALLOW_ANONYMOUS_ACCESS", False)


def anonymous_export_allowed():
    """Check if anonymous export is enabled via settings."""
    return anonymous_access_allowed() and getattr(
        settings, "LINGO_ALLOW_ANONYMOUS_EXPORT", False
    )


def is_lingo_editor(user):
    """Check if a user is a member of the Lingo Editor group (or is a superuser)."""
    if not user.is_authenticated:
        return False
    if user.is_superuser:
        return True
    return user.groups.filter(name=LINGO_EDITOR_GROUP_NAME).exists()


def is_lingo_admin(user):
    """Check if a user is a member of the Lingo Admin group (or is a superuser)."""
    if not user.is_authenticated:
        return False
    if user.is_superuser:
        return True
    return user.groups.filter(name=LINGO_ADMIN_GROUP_NAME).exists()


def is_authenticated_user(user):
    """Check if the request is from a real authenticated user (not anonymous)."""
    return user.is_authenticated and user.username != "anonymous"


def is_lingo_exporter(user):
    """Check if a user is permitted to export Lingo data.

    Lingo editors, Lingo admins, superusers, and members of the Lingo Exporter
    group can always export. Anonymous users can export only when explicitly
    allowed via LINGO_ALLOW_ANONYMOUS_EXPORT.
    """
    if not is_authenticated_user(user):
        return anonymous_export_allowed()
    if is_lingo_editor(user) or is_lingo_admin(user):
        return True
    return user.groups.filter(name=LINGO_EXPORTER_GROUP_NAME).exists()


class LingoAdmin(permissions.BasePermission):
    """DRF permission class requiring membership in the Lingo Admin group."""

    def has_permission(self, request, view):
        return is_lingo_admin(request.user)


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
