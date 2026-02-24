from django.utils.decorators import method_decorator
from django.views.generic import View

from arches.app.utils.decorators import group_required
from arches.app.utils.response import JSONErrorResponse, JSONResponse

from arches_lingo.utils.concept_builder import ConceptBuilder


@method_decorator(
    group_required("RDM Administrator", raise_exception=True), name="dispatch"
)
class SchemeResourceView(View):
    def get(self, request, pk):
        scheme_id = str(pk)
        builder = ConceptBuilder(concept_ids=[])
        builder.populate_schemes([scheme_id])

        scheme = builder.lookup_scheme(scheme_id)
        if scheme is None:
            return JSONErrorResponse(
                title="Scheme not found",
                message=f"No scheme found with id {pk}",
                status=404,
            )

        data = builder.serialize_scheme(scheme, children=False)
        return JSONResponse(data)
