import { ref } from "vue";

import { fetchLingoResourcePartial } from "@/arches_lingo/api.ts";

import type { ResourceSummary } from "@/arches_lingo/types";

const NAME_NODEGROUP_ALIAS = "name";

export function useResourceNameEditor() {
    const selectedResourceInstanceId = ref<string | null>(null);
    const selectedTileId = ref<string | null>(null);
    const isLoadingTile = ref(false);
    const editorKey = ref(0);

    async function selectResource(resource: ResourceSummary) {
        selectedResourceInstanceId.value = resource.resourceinstanceid;
        isLoadingTile.value = true;

        try {
            const partialData = await fetchLingoResourcePartial(
                resource.graph_slug,
                resource.resourceinstanceid,
                NAME_NODEGROUP_ALIAS,
            );
            const nameTiles = partialData?.aliased_data?.name;
            selectedTileId.value =
                Array.isArray(nameTiles) && nameTiles.length > 0
                    ? nameTiles[0].tileid
                    : null;
        } catch {
            selectedTileId.value = null;
        }

        editorKey.value++;
        isLoadingTile.value = false;
    }

    function clearSelection() {
        selectedResourceInstanceId.value = null;
        selectedTileId.value = null;
        editorKey.value++;
    }

    return {
        selectedResourceInstanceId,
        selectedTileId,
        isLoadingTile,
        editorKey,
        selectResource,
        clearSelection,
        NAME_NODEGROUP_ALIAS,
    };
}
