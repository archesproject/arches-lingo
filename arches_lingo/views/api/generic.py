from rest_framework.generics import (
    ListCreateAPIView,
    RetrieveUpdateDestroyAPIView,
)

from arches.app.permissions.rest_framework import RDMAdministrator
from arches.app.views.api.mixins import ArchesModelAPIMixin

from arches_lingo.serializers import (
    LingoResourceSerializer,
    LingoTileSerializer,
    SchemeRightsSerializer,
)


class LingoResourceListCreateView(ArchesModelAPIMixin, ListCreateAPIView):
    permission_classes = [RDMAdministrator]
    serializer_class = LingoResourceSerializer
    pagination_class = None


class LingoResourceDetailView(ArchesModelAPIMixin, RetrieveUpdateDestroyAPIView):
    permission_classes = [RDMAdministrator]
    serializer_class = LingoResourceSerializer


class LingoTileListCreateView(ArchesModelAPIMixin, ListCreateAPIView):
    permission_classes = [RDMAdministrator]
    serializer_class = LingoTileSerializer


class LingoTileDetailView(ArchesModelAPIMixin, RetrieveUpdateDestroyAPIView):
    permission_classes = [RDMAdministrator]
    serializer_class = LingoTileSerializer


class SchemeRightsListCreateView(ArchesModelAPIMixin, ListCreateAPIView):
    permission_classes = [RDMAdministrator]
    serializer_class = SchemeRightsSerializer


class SchemeRightsDetailView(ArchesModelAPIMixin, RetrieveUpdateDestroyAPIView):
    permission_classes = [RDMAdministrator]
    serializer_class = SchemeRightsSerializer
