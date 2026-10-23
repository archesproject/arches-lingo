"""The attribution statement stored against the loaded AAT scheme.

The Getty licence requires attribution, and the statement has to name the date
the copy was taken so readers know how current it is. That date comes from the
archive rather than from when the load happened, so re-running the load against
an older archive states the older date.

The wording follows docs/demo_data_attribution.md, minus the sentence describing
how the demo site presents the vocabulary: this text is stored by any install
that loads the AAT, and whether the result is editable depends on the lifecycle
state the load was given.
"""

from arches.app.models.models import ResourceInstance

from arches_lingo.models import SchemeAttribution

AAT_ATTRIBUTION_TEMPLATE = (
    "This vocabulary represents data from the Art & Architecture Thesaurus® "
    "(AAT), created and maintained by the J. Paul Getty Trust, and used under "
    "the Open Data Commons Attribution License (ODC-By) 1.0. This copy was "
    "extracted on {extraction_date}, and will be updated to the most recent "
    "version of the AAT periodically. A change to the "
    "AAT was made: the top-level (“Top of the AAT hierarchies”) was "
    "omitted to avoid confusion within the scheme’s structure. As a fixed "
    "snapshot from the load date, it may not reflect the current, live version, "
    "and should not be treated as authoritative. To access the official AAT, "
    "please visit: https://www.getty.edu/research/tools/vocabularies/aat/"
)


def format_extraction_date(extraction_date):
    """Render a date the way the attribution statement reads it, e.g. August 1, 2026."""
    return f"{extraction_date.strftime('%B')} {extraction_date.day}, {extraction_date.year}"


def build_aat_attribution(extraction_date):
    return AAT_ATTRIBUTION_TEMPLATE.format(
        extraction_date=format_extraction_date(extraction_date)
    )


def set_scheme_attribution(scheme_resource_instance_id, attribution_text):
    """Store the attribution statement against the scheme, replacing any previous one."""
    scheme_resource = ResourceInstance.objects.get(pk=scheme_resource_instance_id)
    attribution, _created = SchemeAttribution.objects.update_or_create(
        scheme=scheme_resource,
        defaults={"attribution": attribution_text},
    )
    return attribution
