from collections import Counter

from django.utils.translation import gettext as _
from django.views.generic import View

from arches.app.models.models import Language, TileModel
from arches.app.utils.response import JSONErrorResponse, JSONResponse

from arches_querysets.models import ResourceTileTree

from arches_lingo.const import CONCEPT_NAME_NODEGROUP, CONCEPT_NAME_LANGUAGE_NODE
from arches_lingo.mixins.anonymous_access import AnonymousAccessMixin
from arches_lingo.utils.concept_builder import ConceptBuilder


class SchemeResourceView(AnonymousAccessMixin, View):
    def get(self, request, pk):
        scheme_id = str(pk)
        include_top_concepts = bool(request.GET.get("include_top_concepts"))

        builder = ConceptBuilder(concept_ids=[])
        builder.populate_schemes([scheme_id])

        scheme = builder.lookup_scheme(scheme_id)
        if scheme is None:
            return JSONErrorResponse(
                title="Scheme not found",
                message=f"No scheme found with id {pk}",
                status=404,
            )

        if include_top_concepts:
            builder.top_concepts_map()
            top_concept_ids = list(builder.top_concepts.get(scheme_id, set()))
            builder.populate_guide_term_concepts(top_concept_ids)

        data = builder.serialize_scheme(scheme, children=include_top_concepts)
        return JSONResponse(data)


class SchemeLabelCountView(AnonymousAccessMixin, View):
    def get(self, request, pk):
        scheme_id = str(pk)

        Concept = ResourceTileTree.get_tiles("concept")
        concept_ids = list(
            Concept.filter(part_of_scheme__id=scheme_id).values_list("pk", flat=True)
        )

        lang_counter: Counter = Counter()
        if concept_ids:
            tiles = TileModel.objects.filter(
                nodegroup_id=CONCEPT_NAME_NODEGROUP,
                resourceinstance_id__in=concept_ids,
            ).values_list("data", flat=True)

            for data in tiles:
                lang = data.get(CONCEPT_NAME_LANGUAGE_NODE)
                if lang:
                    lang_counter[lang] += 1

        lang_codes = list(lang_counter.keys())
        lang_name_map: dict = {}
        if lang_codes:
            for lang_obj in Language.objects.filter(code__in=lang_codes):
                lang_name_map[lang_obj.code] = lang_obj.name or lang_obj.code

        labels_by_language = [
            {
                "language": lang_name_map.get(code, code),
                "code": code,
                "count": count,
            }
            for code, count in lang_counter.items()
        ]
        labels_by_language.sort(key=lambda x: -x["count"])

        return JSONResponse(labels_by_language)
