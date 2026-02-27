from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _


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
