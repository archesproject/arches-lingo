from rest_framework.generics import (
    ListCreateAPIView,
    RetrieveUpdateDestroyAPIView,
)
from rest_framework.parsers import JSONParser

from arches_querysets.rest_framework.multipart_json_parser import MultiPartJSONParser
from arches_querysets.rest_framework.permissions import RDMAdministrator
from arches_querysets.rest_framework.serializers import ArchesResourceSerializer
from arches_querysets.rest_framework.view_mixins import ArchesModelAPIMixin

from arches_lingo.serializers import LingoTileSerializer


class LingoResourceListCreateView(ArchesModelAPIMixin, ListCreateAPIView):
    permission_classes = [RDMAdministrator]
    serializer_class = ArchesResourceSerializer
    pagination_class = None
    parser_classes = [JSONParser, MultiPartJSONParser]


class LingoResourceDetailView(ArchesModelAPIMixin, RetrieveUpdateDestroyAPIView):
    permission_classes = [RDMAdministrator]
    serializer_class = ArchesResourceSerializer
    parser_classes = [JSONParser, MultiPartJSONParser]


class LingoTileListCreateView(ArchesModelAPIMixin, ListCreateAPIView):
    permission_classes = [RDMAdministrator]
    serializer_class = LingoTileSerializer
    parser_classes = [JSONParser, MultiPartJSONParser]


class LingoTileDetailView(ArchesModelAPIMixin, RetrieveUpdateDestroyAPIView):
    permission_classes = [RDMAdministrator]
    serializer_class = LingoTileSerializer
    parser_classes = [JSONParser, MultiPartJSONParser]
