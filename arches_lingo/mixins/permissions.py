from http import HTTPStatus

from django.http import Http404, HttpResponseNotFound, JsonResponse
from django.utils.decorators import method_decorator
from django.utils.translation import gettext as _
from django.utils.translation import ngettext
from django.views.decorators.csrf import csrf_exempt

from arches.app.utils.response import JSONErrorResponse

from arches_lingo.permissions import (
    anonymous_access_allowed,
    is_authenticated_user,
    is_lingo_admin,
    is_lingo_editor,
    reconciliation_enabled,
)
from arches_lingo.utils.reconciliation.rate_limit import seconds_until_allowed


class AnonymousAccessMixin:
    """Deny requests from anonymous users when anonymous access is disabled."""

    def dispatch(self, request, *args, **kwargs):
        if not anonymous_access_allowed() and not is_authenticated_user(request.user):
            return JsonResponse(
                {"message": _("Authentication required.")},
                status=403,
            )
        return super().dispatch(request, *args, **kwargs)


class ReconciliationAccessMixin:
    """Open the read-only reconciliation service to anonymous, cross-origin callers.

    OpenRefine cannot hold an Arches session or send a CSRF token, and its browser
    UI fetches from another origin, so the service ignores the anonymous access
    setting and allows any origin. While disabled it is indistinguishable from an
    absent endpoint. Callers over LINGO_RECONCILIATION_RATE_LIMIT get a 429.
    """

    @method_decorator(csrf_exempt)
    def dispatch(self, request, *args, **kwargs):
        if not reconciliation_enabled():
            raise Http404()
        retry_after_seconds = seconds_until_allowed(request)
        if retry_after_seconds:
            response = JSONErrorResponse(
                title=_("Too many reconciliation requests."),
                message=ngettext(
                    "Try again in %(seconds)s second.",
                    "Try again in %(seconds)s seconds.",
                    retry_after_seconds,
                )
                % {"seconds": retry_after_seconds},
                status=HTTPStatus.TOO_MANY_REQUESTS,
            )
            response["Retry-After"] = str(retry_after_seconds)
        else:
            try:
                response = super().dispatch(request, *args, **kwargs)
            except Http404:
                response = HttpResponseNotFound()
        # Every response carries it, so the browser lets OpenRefine read its status.
        response["Access-Control-Allow-Origin"] = "*"
        return response


class AuthenticatedUserMixin:
    """Require a real authenticated user (never anonymous) regardless of anonymous access setting."""

    def dispatch(self, request, *args, **kwargs):
        if not is_authenticated_user(request.user):
            return JsonResponse(
                {"message": _("Authentication required.")},
                status=403,
            )
        return super().dispatch(request, *args, **kwargs)


class LingoAdminMixin:
    """Require Lingo admin group membership for all requests."""

    def dispatch(self, request, *args, **kwargs):
        if not is_lingo_admin(request.user):
            return JSONErrorResponse(
                title=_("Permission denied."),
                message=_("You must be a Lingo admin to perform this action."),
                status=HTTPStatus.FORBIDDEN,
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
