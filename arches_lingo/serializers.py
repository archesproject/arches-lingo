from django.utils.translation import gettext as _
from rest_framework.exceptions import ValidationError


from arches_controlled_lists.models import ListItem
from arches_querysets.models import ResourceTileTree
from arches_querysets.rest_framework.serializers import ArchesTileSerializer


class LingoTileSerializer(ArchesTileSerializer):
    def validate_appellative_status(self, data, initial_tile_data):
        if data:
            new_label_lang = None
            new_label_type = None
            if new_label_languages := data.appellative_status_ascribed_name_language:
                new_label_lang = new_label_languages[0]
            if new_label_types := data.appellative_status_ascribed_relation:
                new_label_type = new_label_types[0]

            if new_label_lang and new_label_type:
                resource_pk = (
                    self.initial_data.get("resourceinstance")
                    or self.instance.resourceinstance_id
                )
                scheme = ResourceTileTree.get_tiles(self.graph_slug).get(pk=resource_pk)
                self._check_pref_label_uniqueness(
                    initial_tile_data, scheme, new_label_lang, new_label_type
                )

        return data

    @staticmethod
    def _check_pref_label_uniqueness(
        initial_tile_data, resource, new_label_language, new_label_type
    ):
        try:
            PREF_LABEL = ListItem.objects.get(list_item_values__value="prefLabel")
        except ListItem.MultipleObjectsReturned:
            msg = _(
                "Ask your system administrator to deduplicate the prefLabel list items."
            )
            raise ValidationError(msg)

        for label in resource.aliased_data.appellative_status:
            if (
                label_languages := label.aliased_data.appellative_status_ascribed_name_language
            ):
                label_language = label_languages[0]
            else:
                continue
            if label_types := label.aliased_data.appellative_status_ascribed_relation:
                label_type = label_types[0]
            else:
                continue
            if (
                initial_tile_data.get("tileid") != str(label.tileid)
                and new_label_type.uri == PREF_LABEL.uri
                and label_type.uri == PREF_LABEL.uri
                and label_language.uri == new_label_language.uri
            ):
                msg = _("Only one preferred label per language is permitted.")
                raise ValidationError({"appellative_status": msg})
