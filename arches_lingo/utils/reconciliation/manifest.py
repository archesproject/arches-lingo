from django.conf import settings
from django.urls import reverse
from django.utils.translation import gettext_lazy

from arches_lingo.const import (
    SCHEME_NAME_CONTENT_NODE,
    SCHEME_NAME_LANGUAGE_NODE,
    SCHEME_NAME_NODEGROUP,
    SCHEME_NAME_TYPE_NODE,
)
from arches_lingo.utils.concept_builder import ConceptBuilder
from arches_lingo.utils.reconciliation.labels import choose_display_label
from arches_lingo.utils.reconciliation.visibility import reconcilable_schemes

RECONCILIATION_API_VERSIONS = ["0.1", "0.2"]
SKOS_NAMESPACE = "http://www.w3.org/2004/02/skos/core#"
# OpenRefine's own default; small batches keep its progress bar responsive.
SUGGESTED_BATCH_SIZE = 10
SUGGEST_KINDS = ("entity", "type", "property")
# The reconciliation spec defines the preview iframe size as unitless pixel
# counts, so these cannot be relative units.
PREVIEW_WIDTH_PIXELS = 400
PREVIEW_HEIGHT_PIXELS = 220


PROPERTY_SETTINGS = [
    {
        "name": "lang",
        "label": gettext_lazy("Language"),
        "type": "text",
        "default": "",
        "help_text": gettext_lazy(
            "Language code for labels and notes, such as 'fr'. Leave empty for "
            "the default language, or use '*' for every language."
        ),
    }
]


def public_server_address():
    return settings.PUBLIC_SERVER_ADDRESS.rstrip("/")


def reconciliation_service_url():
    return f"{public_server_address()}{reverse('api-lingo-reconcile')}"


def concept_identifier_space():
    return f"{public_server_address()}{reverse('root')}concept/"


def list_reconcilable_schemes(scheme_ids=None):
    """Return reconciliation types, one per reconcilable scheme, sorted by name."""
    schemes = reconcilable_schemes()
    if scheme_ids is not None:
        schemes = schemes.filter(pk__in=scheme_ids)
    schemes = schemes.annotate(
        labels=ConceptBuilder.labels_subquery(SCHEME_NAME_NODEGROUP)
    )

    reconciliation_types = [
        {
            "id": str(scheme.pk),
            "name": choose_display_label(
                scheme.labels,
                SCHEME_NAME_CONTENT_NODE,
                SCHEME_NAME_TYPE_NODE,
                SCHEME_NAME_LANGUAGE_NODE,
            )
            or str(scheme.name)
            or str(scheme.pk),
        }
        for scheme in schemes
    ]
    return sorted(
        reconciliation_types,
        key=lambda reconciliation_type: reconciliation_type["name"].casefold(),
    )


def build_service_manifest(scheme_id=None):
    """Build the service manifest, scoped to one scheme when ``scheme_id`` is given."""
    reconciliation_types = list_reconcilable_schemes(
        None if scheme_id is None else [scheme_id]
    )

    service_name = settings.LINGO_RECONCILIATION_SERVICE_NAME
    if scheme_id is not None and reconciliation_types:
        service_name = f"{service_name} — {reconciliation_types[0]['name']}"

    identifier_space = concept_identifier_space()
    # Suggest and preview are always the global services, even for one scheme.
    global_service_url = reconciliation_service_url()
    return {
        "versions": RECONCILIATION_API_VERSIONS,
        "name": service_name,
        "identifierSpace": identifier_space,
        "schemaSpace": SKOS_NAMESPACE,
        "defaultTypes": reconciliation_types,
        "view": {"url": f"{identifier_space}{{{{id}}}}"},
        "batchSize": SUGGESTED_BATCH_SIZE,
        "preview": {
            "url": f"{global_service_url}/preview?id={{{{id}}}}",
            "width": PREVIEW_WIDTH_PIXELS,
            "height": PREVIEW_HEIGHT_PIXELS,
        },
        "suggest": {
            suggest_kind: {
                "service_url": global_service_url,
                "service_path": f"/suggest/{suggest_kind}",
            }
            for suggest_kind in SUGGEST_KINDS
        },
        "extend": {
            "propose_properties": {
                "service_url": global_service_url,
                "service_path": "/properties",
            },
            "property_settings": [
                {key: str(value) for key, value in property_setting.items()}
                for property_setting in PROPERTY_SETTINGS
            ],
        },
    }
