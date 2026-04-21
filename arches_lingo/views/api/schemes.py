from http import HTTPStatus

from django.db import models
from django.db.models import Count
from django.db.models.expressions import RawSQL
from django.utils.translation import gettext as _
from django.views.generic import View

from arches.app.models.models import Language, TileModel
from arches.app.utils.response import JSONErrorResponse, JSONResponse

from arches_querysets.models import ResourceTileTree

from arches_lingo.const import CONCEPT_NAME_NODEGROUP, CONCEPT_NAME_LANGUAGE_NODE
from arches_lingo.mixins.permissions import AnonymousAccessMixin
from arches_lingo.utils.concept_builder import ConceptBuilder


class SchemeResourceView(AnonymousAccessMixin, View):
    def get(self, request, pk):
        scheme_id = str(pk)
        include_top_concepts = request.GET.get("include_top_concepts") == "true"

        builder = ConceptBuilder(concept_ids=[])
        builder.populate_schemes([scheme_id])

        scheme = builder.lookup_scheme(scheme_id)
        if scheme is None:
            return JSONErrorResponse(
                title=_("Scheme not found."),
                message=_("No scheme found with id %(scheme_id)s.")
                % {"scheme_id": scheme_id},
                status=HTTPStatus.NOT_FOUND,
            )

        if include_top_concepts:
            builder.top_concepts_map()
            top_concept_ids = list(builder.top_concepts.get(scheme_id, set()))
            builder.populate_concept_type_sets(top_concept_ids)

        return JSONResponse(
            builder.serialize_scheme(
                scheme,
                children=include_top_concepts,
            )
        )


class SchemeLabelCountView(AnonymousAccessMixin, View):
    def get(self, request, pk):
        scheme_id = str(pk)

        Concept = ResourceTileTree.get_tiles("concept")
        concept_ids = Concept.filter(part_of_scheme__id=scheme_id).values("pk")

        rows = list(
            TileModel.objects.filter(
                nodegroup_id=CONCEPT_NAME_NODEGROUP,
                resourceinstance_id__in=concept_ids,
            )
            .values(lang_code=RawSQL("tiledata->>%s", [CONCEPT_NAME_LANGUAGE_NODE]))
            .annotate(count=Count("tileid"))
            .order_by("-count")
        )

        lang_codes = [row["lang_code"] for row in rows if row["lang_code"]]
        lang_name_map: dict = {}
        if lang_codes:
            for lang_obj in Language.objects.filter(code__in=lang_codes):
                lang_name_map[lang_obj.code] = lang_obj.name or lang_obj.code

        labels_by_language = [
            {
                "language": lang_name_map.get(row["lang_code"], row["lang_code"]),
                "code": row["lang_code"],
                "count": row["count"],
            }
            for row in rows
            if row["lang_code"]
        ]

        return JSONResponse(labels_by_language)
