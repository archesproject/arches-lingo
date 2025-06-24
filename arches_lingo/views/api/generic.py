from arches_querysets.rest_framework.generic_views import (
    ArchesResourceDetailView,
    ArchesResourceListCreateView,
    ArchesTileDetailView,
    ArchesTileListCreateView,
)
from arches_querysets.rest_framework.permissions import RDMAdministrator

from arches_lingo.serializers import LingoTileSerializer


class LingoResourceListCreateView(ArchesResourceListCreateView):
    permission_classes = [RDMAdministrator]
    pagination_class = None


class LingoResourceDetailView(ArchesResourceDetailView):
    permission_classes = [RDMAdministrator]


class LingoTileListCreateView(ArchesTileListCreateView):
    permission_classes = [RDMAdministrator]
    serializer_class = LingoTileSerializer


class LingoTileDetailView(ArchesTileDetailView):
    permission_classes = [RDMAdministrator]
    serializer_class = LingoTileSerializer
