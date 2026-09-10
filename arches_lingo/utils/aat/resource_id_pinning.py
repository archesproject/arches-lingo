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
    SELECT tiledata ->> '{const.URI_CONTENT_NODE}' AS uri, resourceinstanceid
      FROM tiles
     WHERE nodegroupid = '{const.URI_NODEGROUP}'
       AND tiledata ->> '{const.URI_CONTENT_NODE}' LIKE %(uri_prefix)s
    UNION ALL
    SELECT tiledata ->> '{const.SCHEME_URI_CONTENT_NODE}' AS uri, resourceinstanceid
      FROM tiles
     WHERE nodegroupid = '{const.SCHEME_URI_NODEGROUP}'
       AND tiledata ->> '{const.SCHEME_URI_CONTENT_NODE}' LIKE %(uri_prefix)s
"""


def snapshot_resource_ids_by_uri(uri_prefix):
    """Return {uri: resourceinstanceid} for resources whose URI tile matches.

    Covers both concept and scheme URI tiles, so a reload reuses the existing
    scheme resource rather than creating a second one alongside it.
    """
    with connection.cursor() as cursor:
        cursor.execute(_URIS_AND_RESOURCE_IDS_SQL, {"uri_prefix": f"{uri_prefix}%"})
        return {uri: resource_id for uri, resource_id in cursor.fetchall() if uri}


def write_resource_id_snapshot(uri_prefix, csv_path):
    """Write the snapshot to CSV and return the number of rows written."""
    resource_ids_by_uri = snapshot_resource_ids_by_uri(uri_prefix)
    with open(csv_path, "w", newline="", encoding="utf-8") as csv_file:
        writer = csv.writer(csv_file)
        writer.writerow(["uri", "resourceinstanceid"])
        for uri, resource_id in sorted(resource_ids_by_uri.items()):
            writer.writerow([uri, resource_id])
    return len(resource_ids_by_uri)
