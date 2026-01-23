from django.db import transaction

from arches_lingo.models import ConceptIdentifierCounter


def allocate_concept_identifier_number(scheme_resource_instance_id, count=1):
    with transaction.atomic():
        counter_record = ConceptIdentifierCounter.objects.select_for_update().get(
            scheme_resource_instance_id=scheme_resource_instance_id
        )

        allocated_number = counter_record.next_number
        counter_record.next_number = allocated_number + count
        counter_record.save(update_fields=["next_number"])

        return allocated_number
