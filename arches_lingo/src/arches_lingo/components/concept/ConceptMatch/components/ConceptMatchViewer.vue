<script setup lang="ts">
import { inject, computed, ref, onMounted, watch } from "vue";
import { RouterLink } from "vue-router";
import { useGettext } from "vue3-gettext";

import Button from "primevue/button";
import Tag from "primevue/tag";

import MetaStringViewer from "@/arches_lingo/components/generic/MetaStringViewer.vue";
import GenericWidget from "@/arches_component_lab/generics/GenericWidget/GenericWidget.vue";

import { resolveConceptURI } from "@/arches_lingo/api.ts";
import { VIEW } from "@/arches_lingo/constants.ts";
import { routeNames } from "@/arches_lingo/routes.ts";
import { useUserStore } from "@/arches_lingo/stores/useUserStore.ts";

import type {
    ConceptMatchStatus,
    MetaStringText,
} from "@/arches_lingo/types.ts";

const props = defineProps<{
    componentName: string;
    graphSlug: string;
    nodegroupAlias: string;
    resourceInstanceId: string | undefined;
    sectionTitle: string;
    tileData: ConceptMatchStatus[];
}>();

const { $gettext } = useGettext();
const { isEditor } = useUserStore();

const openEditor =
    inject<(componentName: string, tileId?: string) => void>("openEditor");

const resourceInstanceLifecycleState = inject<{
    value:
        | {
              can_edit_resource_instances: boolean;
              can_delete_resource_instances: boolean;
          }
        | undefined;
}>("resourceInstanceLifecycleState");

const canEditResourceInstances = computed(() => {
    return Boolean(
        resourceInstanceLifecycleState?.value?.can_edit_resource_instances,
    );
});

const isCreateDisabled = computed(() => {
    return Boolean(
        !props.resourceInstanceId || !canEditResourceInstances.value,
    );
});

const createTooltipText = computed(() => {
    if (!isCreateDisabled.value) {
        return "";
    }

    if (!props.resourceInstanceId) {
        return $gettext(
            "Create a Concept Label before adding matched concepts",
        );
    }

    return $gettext(
        "This concept is not editable in its current lifecycle state",
    );
});

const metaStringLabel = computed<MetaStringText>(() => ({
    deleteConfirm: $gettext(
        "Are you sure you want to delete this relationship?",
    ),
    name: $gettext("Match Type"),
    type: $gettext("Related URI"),
    noRecords: $gettext("No matched concepts were found."),
    sortFields: {
        name: "aliased_data.match_status_ascribed_relation.display_value",
        type: "aliased_data.match_status_ascribed_comparate.display_value",
    },
}));

const resolvedLocalConceptIds = ref<Record<string, string | null>>({});

async function resolveLocalConceptIds() {
    const uris = [
        ...new Set(
            props.tileData
                .map(
                    (tile) =>
                        tile.aliased_data.match_status_ascribed_comparate
                            .display_value,
                )
                .filter((uri) => uri.startsWith("http")),
        ),
    ];

    const results = await Promise.all(
        uris.map(async (uri) => {
            const result = await resolveConceptURI(uri);
            return [uri, result?.resourceinstanceid ?? null] as const;
        }),
    );

    resolvedLocalConceptIds.value = Object.fromEntries(results);
}

onMounted(resolveLocalConceptIds);
watch(() => props.tileData, resolveLocalConceptIds);

function getComparateURI(rowData: ConceptMatchStatus): string {
    return rowData.aliased_data.match_status_ascribed_comparate
        .display_value as string;
}

function localConceptRoute(
    rowData: ConceptMatchStatus,
): { name: string; params: { id: string } } | null {
    const uri = getComparateURI(rowData);
    const conceptId = resolvedLocalConceptIds.value[uri];
    return conceptId
        ? { name: routeNames.concept, params: { id: conceptId } }
        : null;
}

function externalConceptURI(rowData: ConceptMatchStatus): string | null {
    const uri = getComparateURI(rowData);
    return uri.startsWith("http") ? uri : null;
}
</script>

<template>
    <div class="viewer-section">
        <div class="section-header">
            <div class="section-title">
                <h2>{{ props.sectionTitle }}</h2>
                <Tag
                    v-if="props.tileData.length"
                    :value="String(props.tileData.length)"
                    severity="secondary"
                />
            </div>

            <Button
                v-if="isEditor"
                v-tooltip.top="{
                    disabled: Boolean(!isCreateDisabled),
                    value: createTooltipText,
                    showDelay: 300,
                    pt: {
                        text: {
                            style: { fontFamily: 'var(--p-lingo-font-family)' },
                        },
                        arrow: { style: { display: 'none' } },
                    },
                }"
                :disabled="isCreateDisabled"
                :label="$gettext('Add Matched Concept')"
                class="add-button wide"
                icon="pi pi-plus-circle"
                @click="openEditor!(props.componentName)"
            ></Button>
        </div>

        <MetaStringViewer
            :meta-strings="props.tileData"
            :meta-string-text="metaStringLabel"
            :component-name="props.componentName"
            :graph-slug="props.graphSlug"
            :nodegroup-alias="props.nodegroupAlias"
        >
            <template #name="{ rowData }">
                <GenericWidget
                    :graph-slug="props.graphSlug"
                    node-alias="match_status_ascribed_relation"
                    :aliased-node-data="
                        rowData.aliased_data.match_status_ascribed_relation
                    "
                    :mode="VIEW"
                    :should-show-label="false"
                />
            </template>
            <template #type="{ rowData }">
                <RouterLink
                    v-if="localConceptRoute(rowData)"
                    :to="localConceptRoute(rowData)!"
                    class="local-concept-link"
                >
                    {{
                        rowData.aliased_data.match_status_ascribed_comparate
                            .display_value
                    }}
                </RouterLink>
                <Button
                    v-else-if="externalConceptURI(rowData)"
                    :label="
                        rowData.aliased_data.match_status_ascribed_comparate
                            .display_value
                    "
                    variant="link"
                    as="a"
                    :href="externalConceptURI(rowData)!"
                    target="_blank"
                    rel="noopener"
                ></Button>
                <span v-else>
                    {{
                        rowData.aliased_data.match_status_ascribed_comparate
                            .display_value
                    }}
                </span>
            </template>
            <template #drawer="{ rowData }">
                <GenericWidget
                    :graph-slug="props.graphSlug"
                    node-alias="match_status_data_assignment_actor"
                    :aliased-node-data="
                        rowData.aliased_data.match_status_data_assignment_actor
                    "
                    :mode="VIEW"
                />
                <GenericWidget
                    :graph-slug="props.graphSlug"
                    node-alias="match_status_data_assignment_object_used"
                    :aliased-node-data="
                        rowData.aliased_data
                            .match_status_data_assignment_object_used
                    "
                    :mode="VIEW"
                />
            </template>
        </MetaStringViewer>
    </div>
</template>

<style scoped>
.text-link {
    color: var(--p-primary-500);
}

:deep(a) {
    color: var(--p-primary-500);
    padding-left: 0;

    span {
        font-size: var(--p-lingo-font-size-smallnormal);
    }
}

.local-concept-link {
    color: var(--p-primary-500);
    font-size: var(--p-lingo-font-size-smallnormal);
    text-decoration: none;

    &:hover {
        text-decoration: underline;
    }
}
</style>
