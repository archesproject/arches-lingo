from django.db import models


class ConceptIdentifierCounter(models.Model):
    scheme_resource_instance_id = models.UUIDField(unique=True)
    start_number = models.BigIntegerField(default=1)
    next_number = models.BigIntegerField(default=1)

    class Meta:
        db_table = "concept_identifier_counters"
