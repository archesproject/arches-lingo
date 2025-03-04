from rest_framework.generics import (
    ListCreateAPIView,
    RetrieveUpdateDestroyAPIView,
)

from arches.app.permissions.rest_framework import RDMAdministrator
from arches.app.models.serializers import ArchesResourceSerializer, ArchesTileSerializer
from arches.app.views.api.mixins import ArchesModelAPIMixin


class LingoResourceListCreateView(ArchesModelAPIMixin, ListCreateAPIView):
    permission_classes = [RDMAdministrator]
    serializer_class = ArchesResourceSerializer
    pagination_class = None


class LingoResourceDetailView(ArchesModelAPIMixin, RetrieveUpdateDestroyAPIView):
    permission_classes = [RDMAdministrator]
    serializer_class = ArchesResourceSerializer


class LingoTileListCreateView(ArchesModelAPIMixin, ListCreateAPIView):
    permission_classes = [RDMAdministrator]
    serializer_class = ArchesTileSerializer


class LingoTileDetailView(ArchesModelAPIMixin, RetrieveUpdateDestroyAPIView):
    permission_classes = [RDMAdministrator]
    serializer_class = ArchesTileSerializer
