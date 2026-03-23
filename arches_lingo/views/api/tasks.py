from django.utils.translation import gettext as _
from django.views.generic import View

from arches.app.utils.response import JSONErrorResponse, JSONResponse

from arches_lingo.permissions import is_resource_editor
from arches_lingo.utils.tasks import (
    cancel_user_load_event,
    delete_user_load_event,
    get_user_load_events,
)


class UserTaskListView(View):
    """Returns a paginated list of bulk data manager tasks for the authenticated user."""

    def get(self, request):
        if not is_resource_editor(request.user):
            return JSONErrorResponse(
                title=_("Permission denied"),
                message=_("You must be a Resource Editor to view tasks."),
                status=403,
            )

        try:
            page = int(request.GET.get("page", 1))
        except (ValueError, TypeError):
            page = 1

        result = get_user_load_events(request.user, page=page)
        return JSONResponse(result)


class UserTaskDetailView(View):
    """Supports cancelling a running task (POST) or deleting a completed task (DELETE)."""

    def post(self, request, loadid):
        if not is_resource_editor(request.user):
            return JSONErrorResponse(
                title=_("Permission denied"),
                message=_("You must be a Resource Editor to manage tasks."),
                status=403,
            )

        result = cancel_user_load_event(request.user, str(loadid))
        if not result["success"]:
            return JSONErrorResponse(
                title=_("Unable to cancel task"),
                message=result["message"],
                status=400,
            )
        return JSONResponse(result)

    def delete(self, request, loadid):
        if not is_resource_editor(request.user):
            return JSONErrorResponse(
                title=_("Permission denied"),
                message=_("You must be a Resource Editor to manage tasks."),
                status=403,
            )

        result = delete_user_load_event(request.user, str(loadid))
        if not result["success"]:
            return JSONErrorResponse(
                title=_("Unable to delete task"),
                message=result["message"],
                status=400,
            )
        return JSONResponse(result)
