from django.core.exceptions import ValidationError
from django.utils.translation import gettext as _

from arches.app.functions.base import BaseFunction

from arches_controlled_lists.datatypes.datatypes import ReferenceDataType
from arches_controlled_lists.models import ListItem


class ValidateAppellativeStatus(BaseFunction):
    def save(self, tile, request=None, context=None):
        if not hasattr(tile, "appellative_status_ascribed_name_language"):
            tile._enrich(graph_slug="scheme", only=["appellative_status"])
        if (
            new_label_languages := ReferenceDataType().to_python(
                tile.appellative_status_ascribed_name_language
            )
        ) and (
            new_label_types := ReferenceDataType().to_python(
                tile.appellative_status_ascribed_relation
            )
        ):
            self.check_pref_label_uniqueness(
                tile, new_label_languages[0], new_label_types[0]
            )

    @staticmethod
    def check_pref_label_uniqueness(tile, new_label_language, new_label_type):
        try:
            PREF_LABEL = ListItem.objects.get(list_item_values__value="prefLabel")
        except ListItem.MultipleObjectsReturned:
            msg = _(
                "Ask your system administrator to deduplicate the prefLabel list items."
            )
            raise ValidationError(msg)

        for label in tile.resourceinstance.appellative_status or []:
            if label_languages := label.appellative_status_ascribed_name_language:
                label_language = label_languages[0]
            else:
                continue
            if label_types := label.appellative_status_ascribed_relation:
                label_type = label_types[0]
            else:
                continue
            if (
                tile.tileid != label.tileid
                and new_label_type.uri == PREF_LABEL.uri
                and label_type.uri == PREF_LABEL.uri
                and label_language.uri == new_label_language.uri
            ):
                msg = _("Only one preferred label per language is permitted.")
                # Associate the error with one of the relevant nodes.
                raise ValidationError(
                    {"appellative_status_ascribed_name_language": msg}
                )
