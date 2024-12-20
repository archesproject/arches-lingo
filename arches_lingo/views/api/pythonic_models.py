from rest_framework.generics import (
    ListCreateAPIView,
    ListAPIView,
    RetrieveUpdateDestroyAPIView,
)

from arches.app.permissions.rest_framework import RDMAdministrator
from arches.app.views.api.mixins import ArchesModelAPIMixin

from arches_lingo.serializers import (
    ConceptSerializer,
    SchemeCreationSerializer,
    SchemeLabelSerializer,
    SchemeLabelTileSerializer,
    SchemeNamespaceSerializer,
    SchemeSerializer,
    ConceptStatementSerializer,
    SchemeStatementSerializer,
    TextualWorkRdmSystemSerializer,
)


class SchemeListCreateView(ArchesModelAPIMixin, ListCreateAPIView):
    permission_classes = [RDMAdministrator]
    serializer_class = SchemeSerializer
    pagination_class = None


class SchemeDetailView(ArchesModelAPIMixin, RetrieveUpdateDestroyAPIView):
    permission_classes = [RDMAdministrator]
    serializer_class = SchemeSerializer


class SchemeStatementListCreateView(ArchesModelAPIMixin, ListCreateAPIView):
    permission_classes = [RDMAdministrator]
    serializer_class = SchemeStatementSerializer


class SchemeStatementDetailView(ArchesModelAPIMixin, RetrieveUpdateDestroyAPIView):
    permission_classes = [RDMAdministrator]
    serializer_class = SchemeStatementSerializer


class ConceptListCreateView(ArchesModelAPIMixin, ListCreateAPIView):
    permission_classes = [RDMAdministrator]
    serializer_class = ConceptSerializer


class SchemeNamespaceView(ArchesModelAPIMixin, RetrieveUpdateDestroyAPIView):
    permission_classes = [RDMAdministrator]
    serializer_class = SchemeNamespaceSerializer


class SchemeCreationView(ArchesModelAPIMixin, RetrieveUpdateDestroyAPIView):
    permission_classes = [RDMAdministrator]
    serializer_class = SchemeCreationSerializer


class SchemeLabelView(ArchesModelAPIMixin, RetrieveUpdateDestroyAPIView):
    permission_classes = [RDMAdministrator]
    serializer_class = SchemeLabelSerializer


class SchemeLabelTileView(ArchesModelAPIMixin, RetrieveUpdateDestroyAPIView):
    permission_classes = [RDMAdministrator]
    serializer_class = SchemeLabelTileSerializer


class TextualWorkRdmSystemSerializerView(ArchesModelAPIMixin, ListAPIView):
    permission_classes = [RDMAdministrator]
    serializer_class = TextualWorkRdmSystemSerializer
    pagination_class = None


class ConceptDetailView(ArchesModelAPIMixin, RetrieveUpdateDestroyAPIView):
    permission_classes = [RDMAdministrator]
    serializer_class = ConceptSerializer


class ConceptStatementListCreateView(ArchesModelAPIMixin, ListCreateAPIView):
    permission_classes = [RDMAdministrator]
    serializer_class = ConceptStatementSerializer


class ConceptStatementDetailView(ArchesModelAPIMixin, RetrieveUpdateDestroyAPIView):
    permission_classes = [RDMAdministrator]
    serializer_class = ConceptStatementSerializer
