from rest_framework.generics import ListCreateAPIView, RetrieveUpdateDestroyAPIView

from arches.app.permissions.rest_framework import RDMAdministrator
from arches.app.views.api.mixins import ArchesModelAPIMixin

from arches_lingo.serializers import (
    ConceptSerializer,
    SchemeSerializer,
    ConceptStatementSerializer,
    SchemeStatementSerializer,
)


class SchemeListCreateView(ArchesModelAPIMixin, ListCreateAPIView):
    permission_classes = [RDMAdministrator]
    serializer_class = SchemeSerializer


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


class ConceptDetailView(ArchesModelAPIMixin, RetrieveUpdateDestroyAPIView):
    permission_classes = [RDMAdministrator]
    serializer_class = ConceptSerializer


class ConceptStatementListCreateView(ArchesModelAPIMixin, ListCreateAPIView):
    permission_classes = [RDMAdministrator]
    serializer_class = ConceptStatementSerializer


class ConceptStatementDetailView(ArchesModelAPIMixin, RetrieveUpdateDestroyAPIView):
    permission_classes = [RDMAdministrator]
    serializer_class = ConceptStatementSerializer
