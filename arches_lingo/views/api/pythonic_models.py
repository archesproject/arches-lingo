from functools import partial

from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework.exceptions import ValidationError
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

    def get_object(self, user=None):
        ret = super().get_object()
        ret.save = partial(ret.save, user=user)
        return ret

    def update(self, request, *args, **kwargs):
        self.get_object = partial(self.get_object, user=request.user)
        return super().update(request, *args, **kwargs)

    def perform_update(self, serializer):
        """Re-raise ValidationError as DRF ValidationError.

        In 3.0 (2014), DRF decided to stop full_clean()'ing before save(),
        which divorces DRF validation needs from model logic needing to
        support the Django admin or similar ModelFormish patterns.
        The stated reasons were:
            - to avoid needing to know about big & scary full_clean(). Fine.
            - to force expressing validation logic outside of models.
        but to adhere to *that* here would require some way of generically
        validating incoming tile data without knowledge of the resource/graph,
        which isn't practical under this implementation.

        Discussion:
        https://github.com/encode/django-rest-framework/discussions/7850
        """
        try:
            serializer.save()
        except DjangoValidationError as django_error:
            raise ValidationError(detail=django_error) from django_error


class SchemeDetailView(PythonicModelAPIMixin, RetrieveUpdateDestroyAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = SchemeSerializer
    graph_slug = "scheme"


class ConceptDetailView(PythonicModelAPIMixin, RetrieveUpdateDestroyAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = ConceptSerializer
    graph_slug = "concept"
