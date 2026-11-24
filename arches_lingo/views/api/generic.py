from functools import partial

from rest_framework.mixins import DestroyModelMixin

from arches.app.utils.permission_backend import user_can_edit_resource
from arches_querysets.rest_framework.generic_views import (
    ArchesResourceDetailView,
    ArchesResourceListCreateView,
    ArchesTileDetailView,
    ArchesTileListCreateView,
)

from arches_lingo.permissions import ReadOnlyOrLingoEditor
from arches_lingo.serializers import LingoResourceSerializer, LingoTileSerializer


class LingoResourceListCreateView(ArchesResourceListCreateView):
    permission_classes = [ReadOnlyOrLingoEditor]
    pagination_class = None
    serializer_class = LingoResourceSerializer


class LingoResourceDetailView(ArchesResourceDetailView):
    permission_classes = [ReadOnlyOrLingoEditor]
    serializer_class = LingoResourceSerializer

    def get_queryset(self):
        return super().get_queryset().select_related("principaluser")


class LingoTileListCreateView(ArchesTileListCreateView):
    permission_classes = [ReadOnlyOrLingoEditor]
    serializer_class = LingoTileSerializer


class LingoTileDetailView(ArchesTileDetailView):
    permission_classes = [ReadOnlyOrLingoEditor]
    serializer_class = LingoTileSerializer

    def destroy(self, request, *args, **kwargs):
        # Removing a tile edits its resource rather than deleting it, so the
        # lifecycle state's can_edit (not can_delete) flag governs access.
        # Bypasses ArchesModelAPIMixin.destroy, which checks resource deletion.
        self.get_object = partial(
            self.get_object, permission_callable=user_can_edit_resource
        )
        return DestroyModelMixin.destroy(self, request, *args, **kwargs)
