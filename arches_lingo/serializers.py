from django.utils.translation import gettext as _
from rest_framework.exceptions import ValidationError


from arches_controlled_lists.datatypes.datatypes import ReferenceDataType
from arches_controlled_lists.models import ListItem
from arches_querysets.rest_framework.serializers import ArchesTileSerializer


class LingoTileSerializer(ArchesTileSerializer):

    def validate_appellative_status(self, data):
        if data:
            new_label_lang = None
            new_label_type = None
            # TODO: consider having serializer run to_python().
            if new_label_languages := ReferenceDataType().to_python(
                data.get("appellative_status_ascribed_name_language")
            ):
                new_label_lang = new_label_languages[0]
            if new_label_types := ReferenceDataType().to_python(
                data.get("appellative_status_ascribed_relation")
            ):
                new_label_type = new_label_types[0]

            if new_label_lang and new_label_type:
                # Still working on the right API for this.
                # Don't want to do it too eagerly.
                self.instance._enrich(self.graph_slug)
                self._check_pref_label_uniqueness(
                    data, self.instance.resourceinstance, new_label_lang, new_label_type
                )

        return data

    @staticmethod
    def _check_pref_label_uniqueness(
        data, resource, new_label_language, new_label_type
    ):
        try:
            PREF_LABEL = ListItem.objects.get(list_item_values__value="prefLabel")
        except ListItem.MultipleObjectsReturned:
            msg = _(
                "Ask your system administrator to deduplicate the prefLabel list items."
            )
            raise ValidationError(msg)

        for label in resource.appellative_status or []:
            if label_languages := label.appellative_status_ascribed_name_language:
                label_language = label_languages[0]
            else:
                continue
            if label_types := label.appellative_status_ascribed_relation:
                label_type = label_types[0]
            else:
                continue
            if (
                data.get("tileid") != label.tileid
                and new_label_type.uri == PREF_LABEL.uri
                and label_type.uri == PREF_LABEL.uri
                and label_language.uri == new_label_language.uri
            ):
                msg = _("Only one preferred label per language is permitted.")
                raise ValidationError(msg)
