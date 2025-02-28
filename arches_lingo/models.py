from django.db import models

from arches.app.models.models import ResourceInstance

from arches_lingo.querysets import LabelValueQuerySet


class VwLabelValue(models.Model):
    concept = models.ForeignKey(
        ResourceInstance,
        related_name="label_values",
        on_delete=models.DO_NOTHING,
        db_column="conceptid",
    )
    value = models.CharField(db_column="value")

    objects = LabelValueQuerySet.as_manager()

    class Meta:
        managed = False
        db_table = f"arches_lingo__vw_label_values"
