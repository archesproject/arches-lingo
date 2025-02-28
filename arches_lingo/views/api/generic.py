from rest_framework.generics import (
    ListCreateAPIView,
    RetrieveUpdateDestroyAPIView,
)

from arches_querysets.rest_framework.permissions import RDMAdministrator
from arches_querysets.rest_framework.serializers import ArchesResourceSerializer
from arches_querysets.rest_framework.view_mixins import ArchesModelAPIMixin

from arches_lingo.serializers import LingoTileSerializer


class LingoResourceListCreateView(ArchesModelAPIMixin, ListCreateAPIView):
    permission_classes = [RDMAdministrator]
    serializer_class = ArchesResourceSerializer
    pagination_class = None


class LingoResourceDetailView(ArchesModelAPIMixin, RetrieveUpdateDestroyAPIView):
    permission_classes = [RDMAdministrator]
    serializer_class = ArchesResourceSerializer


class LingoTileListCreateView(ArchesModelAPIMixin, ListCreateAPIView):
    permission_classes = [RDMAdministrator]
    serializer_class = LingoTileSerializer


class LingoTileDetailView(ArchesModelAPIMixin, RetrieveUpdateDestroyAPIView):
    permission_classes = [RDMAdministrator]
    serializer_class = LingoTileSerializer
