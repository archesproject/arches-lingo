from http import HTTPStatus

from django.http import JsonResponse
from django.utils.translation import gettext as _

from arches.app.utils.response import JSONErrorResponse

from arches_lingo.permissions import (
    anonymous_access_allowed,
    is_authenticated_user,
    is_lingo_editor,
)


class AnonymousAccessMixin:
    """Deny requests from anonymous users when anonymous access is disabled."""

    def dispatch(self, request, *args, **kwargs):
        if not anonymous_access_allowed() and not is_authenticated_user(request.user):
            return JsonResponse(
                {"message": _("Authentication required.")},
                status=403,
            )
        return super().dispatch(request, *args, **kwargs)


class AuthenticatedUserMixin:
    """Require a real authenticated user (never anonymous) regardless of anonymous access setting."""

    def dispatch(self, request, *args, **kwargs):
        if not is_authenticated_user(request.user):
            return JsonResponse(
                {"message": _("Authentication required.")},
                status=403,
            )
        return super().dispatch(request, *args, **kwargs)


class LingoEditorMixin:
    """Require Lingo editor group membership for all requests."""

    def dispatch(self, request, *args, **kwargs):
        if not is_lingo_editor(request.user):
            return JSONErrorResponse(
                title=_("Permission denied."),
                message=_("You must be a Lingo editor to perform this action."),
                status=HTTPStatus.FORBIDDEN,
            )
        return super().dispatch(request, *args, **kwargs)


class LingoEditorWriteMixin:
    """Require Lingo editor group membership for any non-safe (mutating) request."""

    def dispatch(self, request, *args, **kwargs):
        if request.method not in ("GET", "HEAD", "OPTIONS"):
            if not is_lingo_editor(request.user):
                return JSONErrorResponse(
                    title=_("Permission denied."),
                    message=_("You must be a Lingo editor to perform this action."),
                    status=HTTPStatus.FORBIDDEN,
                )
        return super().dispatch(request, *args, **kwargs)
