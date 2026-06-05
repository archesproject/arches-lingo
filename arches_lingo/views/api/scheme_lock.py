from http import HTTPStatus

from django.utils.translation import gettext as _
from django.views.generic import View

from arches.app.models.models import ResourceInstanceLifecycleState
from arches.app.models.resource import Resource
from arches.app.utils.response import JSONErrorResponse, JSONResponse

from arches_lingo.mixins.permissions import LingoAdminMixin
from arches_lingo.utils.concept_lifecycle import (
    EDITING_STATE_ID,
    LOCKED_STATE_ID,
    RETIRED_STATE_ID,
)


class SchemeLockView(LingoAdminMixin, View):
    def post(self, request, pk):
        try:
            scheme = Resource.objects.select_related(
                "resource_instance_lifecycle_state"
            ).get(pk=pk)
        except Resource.DoesNotExist:
            return JSONErrorResponse(
                title=_("Not found"),
                message=_("Scheme not found."),
                status=HTTPStatus.NOT_FOUND,
            )

        if scheme.resource_instance_lifecycle_state_id == RETIRED_STATE_ID:
            return JSONErrorResponse(
                title=_("Cannot lock"),
                message=_("Retired schemes cannot be locked."),
                status=HTTPStatus.BAD_REQUEST,
            )

        current_state = scheme.resource_instance_lifecycle_state
        scheme.resource_instance_lifecycle_state = (
            ResourceInstanceLifecycleState.objects.get(pk=LOCKED_STATE_ID)
        )
        scheme.save(
            request=request,
            should_update_resource_instance_lifecycle_state=True,
            current_resource_instance_lifecycle_state=current_state,
        )
        return JSONResponse({"locked": True})


class SchemeUnlockView(LingoAdminMixin, View):
    def post(self, request, pk):
        try:
            scheme = Resource.objects.select_related(
                "resource_instance_lifecycle_state"
            ).get(pk=pk)
        except Resource.DoesNotExist:
            return JSONErrorResponse(
                title=_("Not found"),
                message=_("Scheme not found."),
                status=HTTPStatus.NOT_FOUND,
            )

        if scheme.resource_instance_lifecycle_state_id != LOCKED_STATE_ID:
            return JSONErrorResponse(
                title=_("Not locked"),
                message=_("This scheme is not currently locked."),
                status=HTTPStatus.BAD_REQUEST,
            )

        current_state = scheme.resource_instance_lifecycle_state
        scheme.resource_instance_lifecycle_state = (
            ResourceInstanceLifecycleState.objects.get(pk=EDITING_STATE_ID)
        )
        scheme.save(
            request=request,
            should_update_resource_instance_lifecycle_state=True,
            current_resource_instance_lifecycle_state=current_state,
        )
        return JSONResponse({"locked": False})
