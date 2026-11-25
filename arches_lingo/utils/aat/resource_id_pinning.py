"""Keep resource ids stable across a reload.

The SKOS importer derives resource ids with uuid5 from a namespace generated
fresh on every run, so re-importing an unchanged concept would still mint a new
id and orphan anything referring to the old one. Snapshotting the ids a previous
load assigned, keyed by the URI each resource carries, lets the importer put
surviving resources back on the ids they already had.
"""

import csv

from django.db import connection

from arches_lingo import const

_URIS_AND_RESOURCE_IDS_SQL = f"""
    SELECT uri_tile.tiledata ->> '{const.URI_CONTENT_NODE}' AS uri,
           uri_tile.resourceinstanceid
      FROM tiles uri_tile
      JOIN tiles part_of_scheme
        ON part_of_scheme.resourceinstanceid = uri_tile.resourceinstanceid
       AND part_of_scheme.nodegroupid = '{const.CONCEPTS_PART_OF_SCHEME_NODEGROUP_ID}'
     WHERE uri_tile.nodegroupid = '{const.URI_NODEGROUP}'
       AND uri_tile.tiledata ->> '{const.URI_CONTENT_NODE}' LIKE %(uri_prefix)s
       AND part_of_scheme.tiledata
           -> '{const.CONCEPTS_PART_OF_SCHEME_NODEGROUP_ID}' -> 0 ->> 'resourceId'
           = %(scheme_id)s
"""


def snapshot_resource_ids_by_uri(uri_prefix, scheme_resource_id):
    """Return {uri: resourceinstanceid} for the scheme's concepts whose URI matches.

    Only concepts in the scheme are considered, so a URI tile copied onto a
    concept elsewhere cannot pin an id the purge leaves in place.
    """
    with connection.cursor() as cursor:
        cursor.execute(
            _URIS_AND_RESOURCE_IDS_SQL,
            {"uri_prefix": f"{uri_prefix}%", "scheme_id": str(scheme_resource_id)},
        )
        return {uri: resource_id for uri, resource_id in cursor.fetchall() if uri}


def write_resource_id_snapshot(
    uri_prefix, csv_path, scheme_resource_id, include_concepts=True
):
    """Write the snapshot to CSV and return the number of rows written.

    The scheme is pinned under the URI the converted SKOS uses to identify it,
    which is the bare vocabulary prefix. The scheme's own URI tile holds a
    different value -- its Getty subject number -- so without this the scheme
    is never matched and each reload creates a second one alongside the old.

    `include_concepts` off pins the scheme alone, for a reload that gives every
    concept a fresh id but should still replace the scheme in place.
    """
    resource_ids_by_uri = (
        snapshot_resource_ids_by_uri(uri_prefix, scheme_resource_id)
        if include_concepts
        else {}
    )
    resource_ids_by_uri[uri_prefix] = scheme_resource_id
    with open(csv_path, "w", newline="", encoding="utf-8") as csv_file:
        writer = csv.writer(csv_file)
        writer.writerow(["uri", "resourceinstanceid"])
        for uri, resource_id in sorted(resource_ids_by_uri.items()):
            writer.writerow([uri, resource_id])
    return len(resource_ids_by_uri)
