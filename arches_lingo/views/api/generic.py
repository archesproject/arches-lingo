from arches_querysets.rest_framework.generic_views import (
    ArchesResourceDetailView,
    ArchesResourceListCreateView,
    ArchesTileDetailView,
    ArchesTileListCreateView,
)

from arches_lingo.permissions import ReadOnlyOrLingoEditor
from arches_lingo.serializers import LingoTileSerializer


class LingoResourceListCreateView(ArchesResourceListCreateView):
    permission_classes = [ReadOnlyOrLingoEditor]
    pagination_class = None


class LingoResourceDetailView(ArchesResourceDetailView):
    permission_classes = [ReadOnlyOrLingoEditor]


class LingoTileListCreateView(ArchesTileListCreateView):
    permission_classes = [ReadOnlyOrLingoEditor]
    serializer_class = LingoTileSerializer


class LingoTileDetailView(ArchesTileDetailView):
    permission_classes = [ReadOnlyOrLingoEditor]
    serializer_class = LingoTileSerializer
