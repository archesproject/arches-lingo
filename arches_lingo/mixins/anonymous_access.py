from django.http import JsonResponse
from django.utils.translation import gettext as _

from arches_lingo.permissions import anonymous_access_allowed, is_authenticated_user


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
