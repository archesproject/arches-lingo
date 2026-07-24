import uuid

from django.http import Http404, HttpResponse
from django.utils.cache import patch_vary_headers
from django.views import View

from arches.app.models.models import ResourceIdentifier, ResourceInstance

from arches_lingo.permissions import anonymous_access_allowed, is_authenticated_user
from arches_lingo.utils.concept_lifecycle import (
    PUBLICLY_DEREFERENCEABLE_STATE_IDS,
    RETIRED_STATE_ID,
)
from arches_lingo.utils.skos_serializer import (
    NOT_ACCEPTABLE,
    graph_kind_for_graph_id,
    negotiate_rdf_format,
    serialize_resource,
)
from arches_lingo.views.root import LingoRootView


class DereferenceableResourceView(View):
    """Serve a scheme or concept URI as either the HTML app or a SKOS representation.

    The same identity URI is dereferenceable by both browsers and machines:
    an ``Accept`` header (or ``?format=`` override) requesting an RDF serialization
    returns SKOS for that single resource; anything else falls through to the Vue
    single-page application, exactly as before this view existed.
    """

    def get(self, request, *args, **kwargs):
        rdf_format = negotiate_rdf_format(
            request.META.get("HTTP_ACCEPT", ""),
            explicit_format=request.GET.get("format"),
        )

        if rdf_format is None:
            # Default (browsers, */*, no Accept): serve the single-page application.
            return LingoRootView.as_view()(request, *args, **kwargs)

        if rdf_format is NOT_ACCEPTABLE:
            return HttpResponse(
                "The requested representation is not available for this resource.",
                status=406,
                content_type="text/plain",
            )

        resource_id, graph_kind = self._resolve_target(kwargs)
        if resource_id is None or graph_kind is None:
            raise Http404()

        lifecycle_state_id = self._lifecycle_state_id(resource_id)
        if not self._may_dereference(request, lifecycle_state_id):
            raise Http404()

        body, content_type = serialize_resource(
            resource_id,
            graph_kind,
            rdf_format,
            mark_deprecated=lifecycle_state_id == RETIRED_STATE_ID,
        )
        if body is None:
            raise Http404()

        response = HttpResponse(body, content_type=content_type)
        patch_vary_headers(response, ("Accept",))
        response["Content-Location"] = f"{request.path}?format={rdf_format}"
        return response

    def _resolve_target(self, kwargs):
        """Return (resource_id, graph_kind) for the requested URI, or (None, None).

        Slug-based routes carry a scheme/concept identifier; UUID routes carry an
        ``id``. In every case the graph kind is confirmed from the loaded resource
        so that only Lingo schemes/concepts are ever serialized as SKOS.
        """
        identifier = kwargs.get("concept_identifier") or kwargs.get("scheme_identifier")
        if identifier:
            resource_id = (
                ResourceIdentifier.objects.filter(
                    identifier=identifier,
                    source="arches-lingo",
                )
                .values_list("resourceid", flat=True)
                .first()
            )
        else:
            resource_id = kwargs.get("id")

        if resource_id is None:
            return None, None

        graph_id = (
            ResourceInstance.objects.filter(pk=resource_id)
            .values_list("graph_id", flat=True)
            .first()
        )
        if graph_id is None:
            return None, None
        return resource_id, graph_kind_for_graph_id(graph_id)

    def _lifecycle_state_id(self, resource_id):
        raw_state_id = (
            ResourceInstance.objects.filter(pk=resource_id)
            .values_list("resource_instance_lifecycle_state_id", flat=True)
            .first()
        )
        if raw_state_id is None:
            return None
        return uuid.UUID(str(raw_state_id))

    def _may_dereference(self, request, lifecycle_state_id):
        """Authenticated users may preview any state; anonymous consumers get only
        published (publicly dereferenceable) resources, and only when anonymous
        access is enabled."""
        if is_authenticated_user(request.user):
            return True
        if not anonymous_access_allowed():
            return False
        return lifecycle_state_id in PUBLICLY_DEREFERENCEABLE_STATE_IDS
