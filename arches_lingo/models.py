from django.db import models


class ConceptIdentifierCounter(models.Model):
    scheme = models.OneToOneField(
        "models.ResourceInstance",
        to_field="resourceinstanceid",
        db_column="scheme_resource_instance_id",
        on_delete=models.CASCADE,
        related_name="concept_identifier_counter",
    )
    start_number = models.BigIntegerField(default=1)
    next_number = models.BigIntegerField(default=1)

    class Meta:
        db_table = "concept_identifier_counters"
