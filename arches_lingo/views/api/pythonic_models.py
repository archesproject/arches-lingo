from rest_framework.permissions import IsAuthenticated
from rest_framework.generics import RetrieveUpdateDestroyAPIView

from arches.app.models.models import ResourceInstance

from arches_lingo.serializers import ConceptSerializer, SchemeSerializer


class PythonicModelAPIMixin:
    def get_queryset(self):
        fields = self.serializer_class.Meta.fields
        if fields == "__all__":
            fields = None
        return ResourceInstance.as_model(
            self.serializer_class.Meta.graph_slug, only=fields
        )


class SchemeDetailView(PythonicModelAPIMixin, RetrieveUpdateDestroyAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = SchemeSerializer
    graph_slug = "scheme"


class ConceptDetailView(PythonicModelAPIMixin, RetrieveUpdateDestroyAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = ConceptSerializer
    graph_slug = "concept"
