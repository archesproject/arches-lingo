from http import HTTPStatus

from django.utils.decorators import method_decorator
from django.utils.translation import gettext as _
from django.views.generic import View

from arches.app.utils.decorators import group_required
from arches.app.utils.response import JSONErrorResponse, JSONResponse

from arches_lingo.utils.concept_builder import ConceptBuilder


@method_decorator(
    group_required("RDM Administrator", raise_exception=True), name="dispatch"
)
class SchemeResourceView(View):
    def get(self, request):
        scheme_id = request.GET.get("scheme", None)

        if not scheme_id:
            return JSONErrorResponse(
                title=_("Unable to fetch scheme."),
                message=_("Missing required query parameter: scheme"),
                status=HTTPStatus.BAD_REQUEST,
            )

        builder = ConceptBuilder([])
        builder.populate_schemes([scheme_id])

        scheme = builder.lookup_scheme(scheme_id)
        if scheme is None:
            return JSONErrorResponse(
                title=_("Unable to fetch scheme."),
                message=_("Scheme not found."),
                status=HTTPStatus.NOT_FOUND,
            )

        return JSONResponse(
            {
                "data": builder.serialize_scheme(scheme, children=False),
            }
        )
