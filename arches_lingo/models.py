from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _

from arches_lingo.utils.scheme_uri_template import default_scheme_uri_template_value


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


class SavedSearch(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="lingo_saved_searches",
    )
    name = models.CharField(max_length=255)
    query = models.JSONField(
        help_text=_("The advanced search query tree (facets, operators, etc.).")
    )
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = "arches_lingo"
        ordering = ["-updated"]
        verbose_name = _("saved search")
        verbose_name_plural = _("saved searches")

    def __str__(self):
        return self.name


class ConceptSet(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="lingo_concept_sets",
    )
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, default="")
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = "arches_lingo"
        ordering = ["-updated"]
        verbose_name = _("concept set")
        verbose_name_plural = _("concept sets")

    def __str__(self):
        return self.name


class ConceptSetMember(models.Model):
    concept_set = models.ForeignKey(
        ConceptSet,
        on_delete=models.CASCADE,
        related_name="members",
    )
    concept_id = models.UUIDField()
    added = models.DateTimeField(auto_now_add=True)

    class Meta:
        app_label = "arches_lingo"
        unique_together = ("concept_set", "concept_id")
        verbose_name = _("concept set member")
        verbose_name_plural = _("concept set members")

    def __str__(self):
        return f"{self.concept_set.name}: {self.concept_id}"
