<script setup lang="ts">
import { computed, inject, onMounted, ref, watch } from "vue";

import { useGettext } from "vue3-gettext";
import { useToast } from "primevue/usetoast";
import { storeToRefs } from "pinia";

import Button from "primevue/button";
import Skeleton from "primevue/skeleton";

import ConceptHeaderToolbar from "@/arches_lingo/components/concept/ConceptHeader/components/ConceptHeaderToolbar.vue";
import LifecycleStateBadge from "@/arches_lingo/components/generic/LifecycleStateBadge.vue";

import {
    fetchResourceIdentifiers,
    fetchConceptAncestorPaths,
} from "@/arches_lingo/api.ts";
import {
    CONCEPT_TYPE_NODE_ALIAS,
    DEFAULT_ERROR_TOAST_LIFE,
    ERROR,
    SKOS_PREF_LABEL_URI,
    SKOS_ALT_LABEL_URI,
} from "@/arches_lingo/constants.ts";
import { PREF_LABEL, ALT_LABEL } from "@/arches_controlled_lists/constants.ts";

import { extractDescriptors } from "@/arches_lingo/utils.ts";
import { getItemLabel } from "@/arches_controlled_lists/utils.ts";

import { useResourceStore } from "@/arches_lingo/composables/useResourceStore.ts";
import { useConceptStore } from "@/arches_lingo/stores/useConceptStore.ts";
import { useLanguageStore } from "@/arches_lingo/stores/useLanguageStore.ts";

import type { Ref } from "vue";
import type { ResourceInstanceReference } from "@/arches_component_lab/datatypes/resource-instance-list/types.ts";
import type {
    AppellativeStatus,
    ConceptClassificationStatusAliases,
    ConceptHeaderData,
    DataComponentMode,
    Identifier,
    ResourceInstanceLifecycleState,
    ResourceInstanceResult,
    TileData,
} from "@/arches_lingo/types.ts";
import type { Label } from "@/arches_controlled_lists/types.ts";

const props = defineProps<{
    mode: DataComponentMode;
    sectionTitle: string;
    componentName: string;
    graphSlug: string;
    resourceInstanceId: string | undefined;
    nodegroupAlias: string;
}>();

const resourceInstanceLifecycleState = inject<
    Ref<ResourceInstanceLifecycleState | undefined>
>("resourceInstanceLifecycleState");

const { $gettext } = useGettext();
const toast = useToast();

const resourceStore = useResourceStore();
const conceptStore = useConceptStore();

const { selectedLanguage, systemLanguage } = storeToRefs(useLanguageStore());

const concept = ref<ResourceInstanceResult>();
const isTopConcept = ref(false);
const data = ref<ConceptHeaderData>();
const isResourceLoaded = ref(false);
const isIdentifierLoaded = ref(false);
const conceptIdentifierValue = ref<string>();
const conceptTypeTile = ref();
const isWidgetLoading = ref(false);
const ancestorLabelsById = ref<Map<string, Label[]>>(new Map());

const isLoading = computed(function () {
    if (!isIdentifierLoaded.value) return true;
    if (props.resourceInstanceId && !isResourceLoaded.value) return true;
    if (isWidgetLoading.value) return true;

    return false;
});

onMounted(() => {
    if (!props.resourceInstanceId) {
        isIdentifierLoaded.value = true;
        return;
    }

    fetchResourceIdentifiers(props.resourceInstanceId)
        .then((resourceIdentifiers) => {
            conceptIdentifierValue.value = resourceIdentifiers?.[0]?.identifier;
        })
        .catch((error) => {
            toast.add({
                severity: ERROR,
                life: DEFAULT_ERROR_TOAST_LIFE,
                summary: $gettext("Unable to fetch concept"),
                detail: error instanceof Error ? error.message : undefined,
            });
        })
        .finally(() => {
            isIdentifierLoaded.value = true;
        });
});

watch(
    [() => resourceStore.resource.value, () => resourceStore.error.value],
    async ([resource, storeError]) => {
        if (storeError) {
            toast.add({
                severity: ERROR,
                life: DEFAULT_ERROR_TOAST_LIFE,
                summary: $gettext("Unable to fetch concept"),
                detail: storeError.message,
            });
            isResourceLoaded.value = true;
            return;
        }
        if (!resource || !props.resourceInstanceId) return;

        concept.value = resource;
        conceptTypeTile.value =
            resource.aliased_data?.[CONCEPT_TYPE_NODE_ALIAS];
        isTopConcept.value = Boolean(resource.aliased_data?.top_concept_of);
        extractConceptHeaderData(resource);
        isResourceLoaded.value = true;

        fetchConceptAncestorPaths(props.resourceInstanceId)
            .then((paths) => {
                const map = new Map<string, Label[]>();
                for (const path of paths) {
                    for (const node of path.searchResults) {
                        if (node.labels?.length) {
                            map.set(node.id, node.labels);
                        }
                    }
                }
                ancestorLabelsById.value = map;
            })
            .catch(() => {});
    },
    { immediate: true },
);

watch(
    () => selectedLanguage.value.code,
    () => {
        if (concept.value) {
            extractConceptHeaderData(concept.value);
        }
    },
);

function valuetypeFromUri(uri: string | undefined): string {
    if (uri === SKOS_PREF_LABEL_URI) return PREF_LABEL;
    if (uri === SKOS_ALT_LABEL_URI) return ALT_LABEL;
    return "unknown";
}

function extractLabelsFromResource(resource: ResourceInstanceResult): Label[] {
    const tiles: AppellativeStatus[] =
        resource.aliased_data?.appellative_status ?? [];
    const labels: Label[] = [];
    for (const tile of tiles) {
        const aliasedData = tile.aliased_data;
        const contentNodeValue =
            aliasedData.appellative_status_ascribed_name_content.node_value;
        if (!contentNodeValue) continue;
        const typeNode =
            aliasedData.appellative_status_ascribed_relation?.node_value[0];
        const typeUri = typeNode?.data?.uri;
        for (const [languageId, { value }] of Object.entries(
            contentNodeValue,
        )) {
            if (!value) continue;
            labels.push({
                value,
                language_id: languageId,
                valuetype_id: valuetypeFromUri(typeUri),
            });
        }
    }
    return labels;
}

const label = computed<Label | undefined>(function () {
    if (!props.resourceInstanceId) {
        return {
            value: $gettext("New Concept"),
            language_id: selectedLanguage.value.code,
            valuetype_id: PREF_LABEL,
        };
    }

    const storedConcept = conceptStore.findConcept(props.resourceInstanceId);
    if (storedConcept) {
        return getItemLabel(
            { labels: [...storedConcept.labels] },
            selectedLanguage.value.code,
            systemLanguage.value.code,
        );
    }

    if (concept.value) {
        const resourceLabels = extractLabelsFromResource(concept.value);
        if (resourceLabels.length) {
            return getItemLabel(
                { labels: resourceLabels },
                selectedLanguage.value.code,
                systemLanguage.value.code,
            );
        }
    }

    return undefined;
});

const parentConceptLabelMap = computed<Map<string, Label[]>>(function () {
    const map = new Map<string, Label[]>();
    for (const parent of data.value?.parentConcepts ?? []) {
        const id = parentConceptId(parent);
        const storeLabels = conceptStore.findConcept(id)?.labels;
        const ancestorLabels = ancestorLabelsById.value.get(id);
        map.set(id, storeLabels ?? ancestorLabels ?? []);
    }
    return map;
});

const lifecycleStateLabel = computed(function () {
    return resourceInstanceLifecycleState?.value?.name ?? "--";
});

const partOfSchemeId = computed(function () {
    return data.value?.partOfScheme?.node_value?.[0]?.resourceId;
});

function parentConceptId(parent: ResourceInstanceReference): string {
    return parent.resourceId;
}

function extractConceptHeaderData(resource: ResourceInstanceResult) {
    const aliased_data = resource?.aliased_data;

    const name = resource?.name;
    const descriptor = extractDescriptors(resource, selectedLanguage.value);
    const principalUser = resource?.principal_user_display_name ?? undefined;

    const uri = aliased_data?.uri?.aliased_data?.uri_content?.node_value;
    const partOfScheme =
        aliased_data?.part_of_scheme?.aliased_data?.part_of_scheme;
    const schemeId = partOfScheme?.node_value?.[0]?.resourceId;
    const matchingScheme = conceptStore.schemes.find(
        (candidateScheme) => candidateScheme.id === schemeId,
    );
    let schemeLabel: string | undefined;
    if (matchingScheme) {
        schemeLabel = getItemLabel(
            { labels: [...matchingScheme.labels] },
            selectedLanguage.value.code,
            systemLanguage.value.code,
        ).value;
    }

    const parentConcepts = (aliased_data?.classification_status ?? []).flatMap(
        (tile: TileData<ConceptClassificationStatusAliases>) =>
            tile.aliased_data.classification_status_ascribed_classification
                .node_value ?? [],
    );
    const identifier = (aliased_data?.identifier ?? [])
        .map(
            (tile: Identifier) =>
                tile.aliased_data.identifier_content.node_value,
        )
        .filter(Boolean)
        .join(", ");

    data.value = {
        name,
        descriptor,
        uri,
        principalUser,
        lifeCycleState: lifecycleStateLabel.value,
        partOfScheme,
        schemeLabel,
        parentConcepts,
        identifier,
    };
}
</script>

<template>
    <Skeleton
        v-if="isLoading"
        height="9rem"
        class="loading-skeleton"
    />
    <div
        v-show="!isLoading"
        class="concept-header"
    >
        <ConceptHeaderToolbar
            :concept="concept"
            :label="label"
            :graph-slug="graphSlug"
            :resource-instance-id="resourceInstanceId"
            :concept-type-tile="conceptTypeTile"
            :is-top-concept="isTopConcept"
            @update:is-widget-loading="isWidgetLoading = $event"
        />

        <div class="header-content">
            <div class="concept-header-section">
                <div class="header-row">
                    <div class="header-item">
                        <span class="header-item-label">
                            {{ $gettext("Identifier:") }}
                        </span>
                        <span class="header-item-value">
                            {{ conceptIdentifierValue || $gettext("None") }}
                        </span>
                    </div>
                    <div>
                        <span class="header-item-label">{{
                            $gettext("URI: ")
                        }}</span>
                        <Button
                            v-if="data?.uri"
                            :label="data?.uri"
                            class="concept-uri"
                            variant="link"
                            as="a"
                            :href="data?.uri"
                            target="_blank"
                            rel="noopener"
                        ></Button>
                        <span
                            v-else
                            class="header-item-value"
                            >{{ $gettext("No URI assigned") }}</span
                        >
                    </div>
                </div>

                <div class="header-row">
                    <div class="header-item">
                        <span class="header-item-label">
                            {{ $gettext("Scheme:") }}
                        </span>
                        <span class="header-item-value">
                            <RouterLink
                                v-if="data?.partOfScheme"
                                :to="`/scheme/${partOfSchemeId}`"
                            >
                                {{ data?.schemeLabel }}
                            </RouterLink>
                            <span v-else>--</span>
                        </span>
                    </div>

                    <div class="header-item">
                        <span class="header-item-label">
                            {{ $gettext("Life cycle state:") }}
                        </span>
                        <span class="header-item-value">
                            <LifecycleStateBadge
                                :lifecycle-state-id="
                                    resourceInstanceLifecycleState?.id
                                "
                                :lifecycle-state-name="
                                    resourceInstanceLifecycleState?.name
                                "
                            />
                            <span v-if="!resourceInstanceLifecycleState">
                                --
                            </span>
                        </span>
                    </div>
                </div>
            </div>
            <div
                class="header-row"
                :class="{ 'top-concept-owner': isTopConcept }"
            >
                <div
                    v-if="!isTopConcept"
                    class="header-item"
                >
                    <span class="header-item-label">
                        {{ $gettext("Parent Concept(s):") }}
                    </span>
                    <span
                        v-for="parent in data?.parentConcepts"
                        :key="parentConceptId(parent)"
                        class="header-item-value parent-concept"
                    >
                        <RouterLink :to="`/concept/${parentConceptId(parent)}`">
                            {{
                                getItemLabel(
                                    {
                                        labels:
                                            parentConceptLabelMap.get(
                                                parentConceptId(parent),
                                            ) ?? [],
                                    },
                                    selectedLanguage.code,
                                    systemLanguage.code,
                                ).value
                            }}
                        </RouterLink>
                    </span>
                </div>
                <div class="header-item">
                    <span class="header-item-label">
                        {{ $gettext("Owner:") }}
                    </span>
                    <span class="header-item-value">
                        {{ data?.principalUser || $gettext("Anonymous") }}
                    </span>
                </div>
            </div>
        </div>
    </div>
</template>

<style scoped>
.concept-header {
    background: var(--p-header-background);
    border-bottom: 0.0625rem solid var(--p-header-toolbar-border);
    box-sizing: border-box;
}

.header-content {
    padding: 0.5rem 1rem 1rem;
    box-sizing: border-box;
}

.concept-uri {
    font-size: var(--p-lingo-font-size-small);
    font-weight: var(--p-lingo-font-weight-normal);
    color: var(--p-primary-500);
}

.p-button-link {
    padding: 0;
    margin: 0;
}

.header-row {
    display: flex;
    justify-content: space-between;
    align-items: baseline;
    flex-wrap: wrap;
    column-gap: 1rem;
    row-gap: 0.5rem;
    padding-top: 0.5rem;
    min-width: 0;
}

.header-item {
    display: inline-flex;
    align-items: baseline;
    min-width: 0;
}

.header-item-label {
    font-weight: var(--p-lingo-font-weight-normal);
    font-size: var(--p-lingo-font-size-smallnormal);
    color: var(--p-header-item-label);
    margin-inline-end: 0.25rem;
}

.header-item-value {
    font-weight: var(--p-lingo-font-weight-normal);
    font-size: var(--p-lingo-font-size-smallnormal);
    color: var(--p-header-item-label);
    margin-inline-end: 0.25rem;
    min-width: 0;
}

.header-item-value,
:deep(a) {
    font-size: var(--p-lingo-font-size-smallnormal);
    color: var(--p-primary-500);
}

.top-concept-owner {
    justify-self: end;
}

.parent-concept {
    margin-inline-end: 0.5rem;
}

.parent-concept:hover a {
    color: var(--p-primary-700);
}
</style>
