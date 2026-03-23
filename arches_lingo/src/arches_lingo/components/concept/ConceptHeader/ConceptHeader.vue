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
    fetchLingoResource,
    fetchResourceIdentifiers,
} from "@/arches_lingo/api.ts";
import {
    CONCEPT_TYPE_NODE_ALIAS,
    DEFAULT_ERROR_TOAST_LIFE,
    ERROR,
} from "@/arches_lingo/constants.ts";
import { PREF_LABEL } from "@/arches_controlled_lists/constants.ts";

import { extractDescriptors } from "@/arches_lingo/utils.ts";
import { getItemLabel } from "@/arches_controlled_lists/utils.ts";

import { useResourceStore } from "@/arches_lingo/composables/useResourceStore.ts";
import { useConceptStore } from "@/arches_lingo/stores/useConceptStore.ts";
import { useLanguageStore } from "@/arches_lingo/stores/useLanguageStore.ts";
import { useUserStore } from "@/arches_lingo/stores/useUserStore.ts";

import type { Ref } from "vue";
import type {
    ConceptClassificationStatusAliases,
    ConceptHeaderData,
    DataComponentMode,
    Identifier,
    ResourceInstanceLifecycleState,
    ResourceInstanceResult,
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

const userStore = useUserStore();
const resourceStore = useResourceStore();
const conceptStore = useConceptStore();

const { selectedLanguage, systemLanguage } = storeToRefs(useLanguageStore());

const concept = ref<ResourceInstanceResult>();
const isTopConcept = ref(false);
const data = ref<ConceptHeaderData>();
const isLoading = ref(true);
const conceptIdentifierValue = ref<string>();
const conceptTypeTile = ref();

onMounted(async () => {
    try {
        const resourceInstanceId = props.resourceInstanceId;
        if (!resourceInstanceId) return;

        const [fetchedConcept, resourceIdentifiers] = await Promise.all([
            fetchLingoResource(props.graphSlug, resourceInstanceId),
            fetchResourceIdentifiers(resourceInstanceId),
        ]);

        concept.value = fetchedConcept;
        conceptTypeTile.value =
            concept.value?.aliased_data?.[CONCEPT_TYPE_NODE_ALIAS];
        conceptIdentifierValue.value = resourceIdentifiers?.[0]?.identifier;

        extractConceptHeaderData(fetchedConcept);
    } catch (error) {
        toast.add({
            severity: ERROR,
            life: DEFAULT_ERROR_TOAST_LIFE,
            summary: $gettext("Unable to fetch concept"),
            detail: error instanceof Error ? error.message : undefined,
        });
    } finally {
        isLoading.value = false;
    }
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
            isLoading.value = false;
            return;
        }
        if (!resource || !props.resourceInstanceId) return;

        concept.value = resource;
        conceptTypeTile.value =
            resource.aliased_data?.[CONCEPT_TYPE_NODE_ALIAS];
        isTopConcept.value = Boolean(resource.aliased_data?.top_concept_of);
        extractConceptHeaderData(resource);
        isLoading.value = false;
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

const label = computed<Label | undefined>(function () {
    if (!props.resourceInstanceId) {
        return {
            value: $gettext("New Concept"),
            language_id: selectedLanguage.value.code,
            valuetype_id: PREF_LABEL,
        };
    }

    const storedConcept = conceptStore.findConcept(props.resourceInstanceId);
    if (!storedConcept) return undefined;

    return getItemLabel(
        { labels: [...storedConcept.labels] },
        selectedLanguage.value.code,
        systemLanguage.value.code,
    );
});

const parentConceptLabelMap = computed<Map<string, Label[]>>(function () {
    const map = new Map<string, Label[]>();
    for (const parent of data.value?.parentConcepts ?? []) {
        const id = parent.details[0]?.resource_id;

        if (id) {
            map.set(id, conceptStore.findConcept(id)?.labels ?? []);
        }
    }
    return map;
});

const lifecycleStateLabel = computed(function () {
    return resourceInstanceLifecycleState?.value?.name ?? "--";
});

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

    const parentConcepts = (aliased_data?.classification_status || []).flatMap(
        (tile: ConceptClassificationStatusAliases) =>
            tile?.aliased_data?.classification_status_ascribed_classification ||
            [],
    );
    const identifier = (aliased_data?.identifier || [])
        .map(
            (tile: Identifier) =>
                tile?.aliased_data?.identifier_content?.node_value,
        )
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
        v-if="isLoading || !userStore.user"
        class="loading-skeleton"
    />
    <div
        v-else
        class="concept-header"
    >
        <ConceptHeaderToolbar
            :concept="concept"
            :label="label"
            :graph-slug="graphSlug"
            :resource-instance-id="resourceInstanceId"
            :concept-type-tile="conceptTypeTile"
            :is-top-concept="isTopConcept"
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
                                v-if="data?.partOfScheme?.node_value"
                                :to="`/scheme/${data?.partOfScheme?.node_value?.[0]?.resourceId}`"
                            >
                                {{
                                    data?.schemeLabel ||
                                    data?.partOfScheme?.display_value
                                }}
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
                        :key="parent.details[0].resource_id"
                        class="header-item-value parent-concept"
                    >
                        <RouterLink
                            :to="`/concept/${parent.details[0].resource_id}`"
                        >
                            {{
                                getItemLabel(
                                    {
                                        labels:
                                            parentConceptLabelMap.get(
                                                parent.details[0].resource_id,
                                            ) ?? [],
                                    },
                                    selectedLanguage.code,
                                    systemLanguage.code,
                                ).value || parent.details[0].display_value
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
    padding-top: 0rem;
    padding-bottom: 1rem;
    background: var(--p-header-background);
    border-bottom: 0.0625rem solid var(--p-header-toolbar-border);
    min-height: 8.5rem;
    box-sizing: border-box;
}

.header-content {
    padding-top: 0.75rem;
    padding-inline-start: 1rem;
    padding-inline-end: 1rem;
    box-sizing: border-box;
}

.loading-skeleton {
    width: 100%;
    height: 9rem;
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
    row-gap: 0.25rem;
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
