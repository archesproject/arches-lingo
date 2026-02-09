from django.conf import settings
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


def default_scheme_uri_template_value():
    return (
        f"{settings.PUBLIC_SERVER_ADDRESS.rstrip('/')}"
        "/schemes/<scheme_identifier>/concepts/<concept_identifier>"
    )


class SchemeURITemplate(models.Model):
    scheme = models.OneToOneField(
        "models.ResourceInstance",
        to_field="resourceinstanceid",
        db_column="scheme_resource_instance_id",
        on_delete=models.CASCADE,
        related_name="scheme_uri_template",
    )
    url_template = models.TextField(default=default_scheme_uri_template_value)

    class Meta:
        db_table = "scheme_uri_templates"
