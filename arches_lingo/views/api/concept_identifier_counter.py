from arches.app.utils.betterJSONSerializer import JSONDeserializer, JSONSerializer
from arches.app.utils.response import JSONResponse, JSONErrorResponse
from arches.app.views.api import APIBase

from arches_lingo.models import ConceptIdentifierCounter


class ConceptIdentifierCounterView(APIBase):
    def get(self, request, scheme_resource_instance_id):
        concept_identifier_counter = ConceptIdentifierCounter.objects.filter(
            scheme_resource_instance_id=scheme_resource_instance_id
        ).first()

        if not concept_identifier_counter:
            return JSONErrorResponse(
                "ConceptIdentifierCounter not found for the given scheme_resource_instance_id.",
                status=404,
            )

        return JSONResponse(concept_identifier_counter)

    def post(self, request, scheme_resource_instance_id):
        request_json = JSONDeserializer().deserialize(request.body)

        current_concept_identifier_counter = ConceptIdentifierCounter.objects.filter(
            scheme_resource_instance_id=scheme_resource_instance_id
        ).first()

        start_number = request_json.get("start_number", 1)

        if current_concept_identifier_counter:
            if (
                current_concept_identifier_counter.start_number
                != current_concept_identifier_counter.next_number
            ):
                return JSONErrorResponse(
                    "ConceptIdentifierCounter cannot be edited because it has already been used.",
                    status=400,
                )

            current_concept_identifier_counter.start_number = start_number
            current_concept_identifier_counter.next_number = start_number
            current_concept_identifier_counter.save(
                update_fields=["start_number", "next_number"]
            )

            return JSONResponse(current_concept_identifier_counter)

        concept_identifier_counter = ConceptIdentifierCounter.objects.create(
            scheme_resource_instance_id=scheme_resource_instance_id,
            start_number=start_number,
            next_number=start_number,
        )

        return JSONResponse(concept_identifier_counter)
