<script setup lang="ts">
import { computed, ref, watch } from "vue";
import { useGettext } from "vue3-gettext";

import Button from "primevue/button";
import InputText from "primevue/inputtext";
import Select from "primevue/select";
import ToggleButton from "primevue/togglebutton";

import { storeToRefs } from "pinia";

import {
    fetchConceptResources,
    fetchContributors,
    fetchSources,
} from "@/arches_lingo/api.ts";
import { useLanguageStore } from "@/arches_lingo/stores/useLanguageStore.ts";
import { getItemLabel } from "@/arches_controlled_lists/utils.ts";
import { getParentLabels } from "@/arches_lingo/utils.ts";

import type { VirtualScrollerLazyEvent } from "primevue/virtualscroller";

import type {
    AdvancedSearchOptions,
    ConceptSetItem,
    FacetType,
    MatchMode,
    SchemeOption,
    SearchCondition,
    SearchResultItem,
} from "@/arches_lingo/types.ts";

const { $gettext } = useGettext();

const { selectedLanguage, systemLanguage } = storeToRefs(useLanguageStore());

const props = defineProps<{
    condition: SearchCondition;
    options: AdvancedSearchOptions;
    conceptSets: ConceptSetItem[];
}>();

const emit = defineEmits<{
    (event: "update:condition", value: SearchCondition): void;
    (event: "remove"): void;
}>();

const facetTypes = computed<{ label: string; value: FacetType }[]>(() => [
    { label: $gettext("Label"), value: "label" },
    { label: $gettext("Note"), value: "note" },
    { label: $gettext("Language"), value: "language" },
    { label: $gettext("Concept Type"), value: "concept_type" },
    {
        label: $gettext("Hierarchical Relationship"),
        value: "relationship_hierarchical",
    },
    {
        label: $gettext("Associated Relationship"),
        value: "relationship_associated",
    },
    { label: $gettext("Matched URI"), value: "match_uri" },
    { label: $gettext("Scheme"), value: "scheme" },
    { label: $gettext("Top Concept"), value: "top_concept" },
    { label: $gettext("URI"), value: "uri" },
    { label: $gettext("Identifier"), value: "identifier" },
    { label: $gettext("Lifecycle State"), value: "lifecycle_state" },
    { label: $gettext("Concept Set"), value: "concept_set" },
    { label: $gettext("Source"), value: "attribution_source" },
    { label: $gettext("Contributor"), value: "attribution_contributor" },
]);

const matchModes = computed<{ label: string; value: MatchMode }[]>(() => [
    { label: $gettext("Contains"), value: "contains" },
    { label: $gettext("Exact"), value: "exact" },
    { label: $gettext("Starts with"), value: "starts_with" },
    { label: $gettext("Ends with"), value: "ends_with" },
    { label: $gettext("Exists (any value)"), value: "exists" },
]);

const hierarchyDirections = computed(() => [
    { label: $gettext("Broader (parent of)"), value: "broader" },
    { label: $gettext("Narrower (child of)"), value: "narrower" },
]);

const searchTextPlaceholder = computed(() => $gettext("Search text..."));
const noConceptsFoundMessage = computed(() => $gettext("No concepts found"));
const searchConceptsFilterPlaceholder = computed(() =>
    $gettext("Search concepts..."),
);
const selectConceptPlaceholder = computed(() => $gettext("Select concept..."));
const anyTypePlaceholder = computed(() => $gettext("Any type"));
const anyLanguagePlaceholder = computed(() => $gettext("Any language"));
const selectLanguagePlaceholder = computed(() => $gettext("Select language"));
const selectSchemePlaceholder = computed(() => $gettext("Select scheme"));
const anyScheme = computed(() => $gettext("Any scheme"));
const selectStatePlaceholder = computed(() => $gettext("Select state"));
const selectConceptSetPlaceholder = computed(() =>
    $gettext("Select concept set"),
);
const selectConceptTypePlaceholder = computed(() =>
    $gettext("Select concept type"),
);
const removeConditionLabel = computed(() => $gettext("Remove condition"));

const conceptItemSize = 36;
const conceptOptions = ref<SearchResultItem[]>([]);
const isLoadingConcepts = ref(false);
const conceptSearchPage = ref(0);
const conceptSearchTotalCount = ref(0);
const preloadedConceptOptions = ref<SearchResultItem[]>([]);
let conceptFilterDebounceTimer: ReturnType<typeof setTimeout> | null = null;
let activeConceptRequestId = 0;

const sourceSearchResults = ref<
    { display_value: string; resource_id: string }[]
>([]);
const isLoadingSources = ref(false);
let sourceSearchTimeout: ReturnType<typeof setTimeout> | null = null;

const contributorSearchResults = ref<
    { display_value: string; resource_id: string }[]
>([]);
const isLoadingContributors = ref(false);
let contributorSearchTimeout: ReturnType<typeof setTimeout> | null = null;

function onConceptFilter(event: { value: string }) {
    conceptOptions.value = preloadedConceptOptions.value;
    if (conceptFilterDebounceTimer) {
        clearTimeout(conceptFilterDebounceTimer);
    }
    conceptFilterDebounceTimer = setTimeout(() => {
        loadConceptPage(1, event.value);
    }, 300);
}

function mergeSelectedIntoOptions(
    fetchedOptions: SearchResultItem[],
): SearchResultItem[] {
    const fetchedIds = new Set(fetchedOptions.map((o) => o.id));
    const selectedId =
        typeof props.condition.value === "string" ? props.condition.value : "";
    if (!selectedId) return fetchedOptions;
    const alreadySelected = preloadedConceptOptions.value.find(
        (o) => o.id === selectedId && !fetchedIds.has(o.id),
    );
    return alreadySelected
        ? [alreadySelected, ...fetchedOptions]
        : fetchedOptions;
}

async function loadConceptPage(page: number, filterTerm?: string) {
    const requestId = ++activeConceptRequestId;
    try {
        isLoadingConcepts.value = true;
        const parsedResponse = await fetchConceptResources(
            filterTerm || "",
            conceptItemSize,
            page,
        );
        if (requestId !== activeConceptRequestId) return;
        parsedResponse.data.forEach((option: SearchResultItem) => {
            option.label = getItemLabel(
                option,
                selectedLanguage.value.code,
                systemLanguage.value.code,
            ).value;
        });
        if (page === 1) {
            conceptOptions.value = mergeSelectedIntoOptions(
                parsedResponse.data,
            );
        } else {
            conceptOptions.value = [
                ...conceptOptions.value,
                ...parsedResponse.data,
            ];
        }
        conceptSearchPage.value = parsedResponse.current_page;
        conceptSearchTotalCount.value = parsedResponse.total_results;
    } catch {
        if (requestId === activeConceptRequestId) {
            conceptOptions.value = preloadedConceptOptions.value;
        }
    } finally {
        if (requestId === activeConceptRequestId) {
            isLoadingConcepts.value = false;
        }
    }
}

async function onConceptLazyLoad(event?: VirtualScrollerLazyEvent) {
    if (isLoadingConcepts.value) return;
    if (
        conceptSearchTotalCount.value > 0 &&
        conceptOptions.value.length >= conceptSearchTotalCount.value
    ) {
        return;
    }
    if (event && event.last < conceptOptions.value.length - 1) return;
    if (!event && conceptOptions.value.length > 0) return;
    await loadConceptPage((conceptSearchPage.value || 0) + 1);
}

async function preloadSelectedConcepts(conceptId: string) {
    if (!conceptId) {
        preloadedConceptOptions.value = [];
        return;
    }
    try {
        const parsedResponse = await fetchConceptResources(
            "",
            1,
            1,
            undefined,
            undefined,
            [conceptId],
        );
        parsedResponse.data.forEach((option: SearchResultItem) => {
            option.label = getItemLabel(
                option,
                selectedLanguage.value.code,
                systemLanguage.value.code,
            ).value;
        });
        preloadedConceptOptions.value = parsedResponse.data;
        conceptOptions.value = parsedResponse.data;
    } catch {
        preloadedConceptOptions.value = [];
    }
}

function onConceptSelectionChange(selectedId: string | undefined) {
    if (selectedId) {
        const selectedOption = conceptOptions.value.find(
            (o) => o.id === selectedId,
        );
        if (selectedOption) {
            preloadedConceptOptions.value = [selectedOption];
        }
    } else {
        preloadedConceptOptions.value = [];
    }
    updateField("value", selectedId ?? "");
}

function onSourceFilter(event: { value: string }) {
    if (sourceSearchTimeout) {
        clearTimeout(sourceSearchTimeout);
    }
    sourceSearchTimeout = setTimeout(async () => {
        await loadSources(event.value);
    }, 400);
}

async function loadSources(term?: string) {
    try {
        isLoadingSources.value = true;
        const result = await fetchSources(term || "", 50, 0);
        sourceSearchResults.value = (result.results || []).map(
            (item: { resourceinstanceid: string; display_name: string }) => ({
                display_value: item.display_name || item.resourceinstanceid,
                resource_id: item.resourceinstanceid,
            }),
        );
    } catch {
        sourceSearchResults.value = [];
    } finally {
        isLoadingSources.value = false;
    }
}

function onContributorFilter(event: { value: string }) {
    if (contributorSearchTimeout) {
        clearTimeout(contributorSearchTimeout);
    }
    contributorSearchTimeout = setTimeout(async () => {
        await loadContributors(event.value);
    }, 400);
}

async function loadContributors(term?: string) {
    try {
        isLoadingContributors.value = true;
        const result = await fetchContributors(term || "", 50, 0);
        contributorSearchResults.value = (result.results || []).map(
            (item: { resourceinstanceid: string; display_name: string }) => ({
                display_value: item.display_name || item.resourceinstanceid,
                resource_id: item.resourceinstanceid,
            }),
        );
    } catch {
        contributorSearchResults.value = [];
    } finally {
        isLoadingContributors.value = false;
    }
}

async function preloadSelectedSource(resourceId: string) {
    try {
        const result = await fetchSources("", 1, 0, [resourceId]);
        sourceSearchResults.value = (result.results || []).map(
            (item: { resourceinstanceid: string; display_name: string }) => ({
                display_value: item.display_name || item.resourceinstanceid,
                resource_id: item.resourceinstanceid,
            }),
        );
    } catch {
        sourceSearchResults.value = [];
    }
}

async function preloadSelectedContributor(resourceId: string) {
    try {
        const result = await fetchContributors("", 1, 0, [resourceId]);
        contributorSearchResults.value = (result.results || []).map(
            (item: { resourceinstanceid: string; display_name: string }) => ({
                display_value: item.display_name || item.resourceinstanceid,
                resource_id: item.resourceinstanceid,
            }),
        );
    } catch {
        contributorSearchResults.value = [];
    }
}

// Preload selected concepts when a relationship facet is loaded with existing values
watch(
    () => props.condition.facet,
    (facet) => {
        if (
            facet === "relationship_hierarchical" ||
            facet === "relationship_associated"
        ) {
            const currentValue = props.condition.value;
            if (typeof currentValue === "string" && currentValue) {
                preloadSelectedConcepts(currentValue);
            }
        }
    },
    { immediate: true },
);

// Preload selected source/contributor when an attribution facet is loaded with an existing value
watch(
    () => [props.condition.facet, props.condition.value] as const,
    ([facet, value]) => {
        if (typeof value !== "string" || !value) return;
        if (facet === "attribution_source") {
            preloadSelectedSource(value);
        } else if (facet === "attribution_contributor") {
            preloadSelectedContributor(value);
        }
    },
    { immediate: true },
);

const currentMatchMode = computed(
    () => props.condition.match_mode || "contains",
);

const isExistsMode = computed(() => currentMatchMode.value === "exists");

const showValueInput = computed(() => {
    if (isExistsMode.value) return false;
    const facet = props.condition.facet;
    return ["label", "note", "match_uri", "uri", "identifier"].includes(facet);
});

const showConceptPicker = computed(() =>
    ["relationship_hierarchical", "relationship_associated"].includes(
        props.condition.facet,
    ),
);

const showLabelTypeDropdown = computed(() => props.condition.facet === "label");
const showNoteTypeDropdown = computed(() => props.condition.facet === "note");

const showLanguageDropdown = computed(() =>
    ["label", "note"].includes(props.condition.facet),
);

const showLanguageSelect = computed(() => props.condition.facet === "language");
const showSchemeSelect = computed(() => props.condition.facet === "scheme");

const showTopConceptSchemeSelect = computed(
    () => props.condition.facet === "top_concept",
);

const schemeDisplayOptions = computed(() =>
    props.options.schemes.map((scheme: SchemeOption) => ({
        id: scheme.id,
        label: getItemLabel(
            scheme,
            selectedLanguage.value.code,
            systemLanguage.value.code,
        ).value,
    })),
);

const showLifecycleSelect = computed(
    () => props.condition.facet === "lifecycle_state",
);

const showConceptSetSelect = computed(
    () => props.condition.facet === "concept_set",
);

const showConceptTypeDropdown = computed(
    () => props.condition.facet === "concept_type",
);

const showDirectionSelect = computed(
    () => props.condition.facet === "relationship_hierarchical",
);

const showCascadeToggle = computed(
    () => props.condition.facet === "relationship_hierarchical",
);

const showSourcePicker = computed(
    () => props.condition.facet === "attribution_source" && !isExistsMode.value,
);

const showContributorPicker = computed(
    () =>
        props.condition.facet === "attribution_contributor" &&
        !isExistsMode.value,
);

const showAttributionMatchMode = computed(() =>
    ["attribution_source", "attribution_contributor"].includes(
        props.condition.facet,
    ),
);

const attributionMatchModes = computed<{ label: string; value: MatchMode }[]>(
    () => [{ label: $gettext("Exists (any value)"), value: "exists" }],
);

const noSourcesFoundMessage = $gettext("No sources found");
const searchSourcesFilterPlaceholder = $gettext("Search sources...");
const selectSourcePlaceholder = $gettext("Select source...");
const noContributorsFoundMessage = $gettext("No contributors found");
const searchContributorsFilterPlaceholder = $gettext("Search contributors...");
const selectContributorPlaceholder = $gettext("Select contributor...");

const showMatchMode = computed(() => {
    return ["label", "note", "match_uri", "uri", "identifier"].includes(
        props.condition.facet,
    );
});

function updateField(field: keyof SearchCondition, value: string | string[]) {
    const updated = { ...props.condition, [field]: value };
    emit("update:condition", updated);
}

function updateFacet(facet: FacetType) {
    const updated: SearchCondition = {
        id: props.condition.id,
        facet,
        value: "",
    };
    conceptOptions.value = [];
    preloadedConceptOptions.value = [];
    conceptSearchPage.value = 0;
    conceptSearchTotalCount.value = 0;
    emit("update:condition", updated);
}

function updateMatchMode(mode: MatchMode) {
    const updated = { ...props.condition, match_mode: mode };
    if (mode === "exists") {
        updated.value = "";
    }
    emit("update:condition", updated);
}

function updateAttributionMatchMode(val: MatchMode | null) {
    const updated = { ...props.condition, value: "" };
    if (val === "exists") {
        updated.match_mode = "exists";
    } else {
        delete updated.match_mode;
    }
    emit("update:condition", updated);
}

function toggleNegated() {
    const updated = {
        ...props.condition,
        negated: !props.condition.negated,
    };
    emit("update:condition", updated);
}

function toggleCascade() {
    const updated = {
        ...props.condition,
        cascade: !props.condition.cascade,
    };
    emit("update:condition", updated);
}
</script>

<template>
    <div class="facet-row">
        <!-- Negation toggle -->
        <ToggleButton
            :model-value="!!condition.negated"
            :on-label="$gettext('NOT')"
            :off-label="$gettext('NOT')"
            class="negation-toggle"
            :class="{ 'negation-active': condition.negated }"
            @update:model-value="toggleNegated"
        />

        <!-- Facet type selector -->
        <Select
            :model-value="condition.facet"
            :options="facetTypes"
            option-label="label"
            option-value="value"
            :placeholder="$gettext('Select facet')"
            class="facet-type-dropdown"
            @update:model-value="updateFacet"
        />

        <!-- Match mode (for text-based facets) -->
        <Select
            v-if="showMatchMode"
            :model-value="currentMatchMode"
            :options="matchModes"
            option-label="label"
            option-value="value"
            class="match-mode-dropdown"
            @update:model-value="updateMatchMode"
        />

        <Select
            v-if="showAttributionMatchMode"
            :model-value="isExistsMode ? 'exists' : null"
            :options="attributionMatchModes"
            option-label="label"
            option-value="value"
            :placeholder="$gettext('Is attributed to...')"
            :show-clear="true"
            class="match-mode-dropdown"
            @update:model-value="updateAttributionMatchMode"
        />

        <!-- Text input for label, note, URI, identifier, match_uri -->
        <InputText
            v-if="showValueInput"
            :model-value="condition.value as string"
            :placeholder="searchTextPlaceholder"
            class="facet-value-input"
            @update:model-value="
                (val: string | undefined) => updateField('value', val ?? '')
            "
        />

        <!-- Concept picker for hierarchical and associated relationships -->
        <Select
            v-if="showConceptPicker"
            option-label="label"
            option-value="id"
            :filter="true"
            :empty-filter-message="
                isLoadingConcepts
                    ? $gettext('Searching...')
                    : noConceptsFoundMessage
            "
            :filter-placeholder="searchConceptsFilterPlaceholder"
            :loading="isLoadingConcepts"
            :model-value="
                typeof condition.value === 'string' ? condition.value : ''
            "
            :options="conceptOptions"
            :placeholder="selectConceptPlaceholder"
            :show-clear="true"
            :virtual-scroller-options="{
                itemSize: conceptItemSize,
                lazy: true,
                loading: isLoadingConcepts,
                onLazyLoad: onConceptLazyLoad,
                resizeDelay: 200,
            }"
            :auto-filter-focus="true"
            class="facet-value-input"
            @before-show="loadConceptPage(1)"
            @filter="onConceptFilter"
            @update:model-value="onConceptSelectionChange"
        >
            <template #option="slotProps">
                <div>
                    <span>
                        {{
                            getItemLabel(
                                slotProps.option,
                                selectedLanguage.code,
                                systemLanguage.code,
                            ).value
                        }}
                    </span>
                    <span class="concept-hierarchy">
                        [
                        {{
                            getParentLabels(
                                slotProps.option,
                                selectedLanguage.code,
                                systemLanguage.code,
                            )
                        }}
                        ]
                    </span>
                </div>
            </template>
        </Select>

        <!-- Label type filter (from controlled list) -->
        <Select
            v-if="showLabelTypeDropdown"
            :model-value="condition.label_type"
            :options="options.label_types"
            option-label="label"
            option-value="value"
            :placeholder="anyTypePlaceholder"
            show-clear
            class="facet-sub-dropdown"
            @update:model-value="
                (val: string | undefined) =>
                    updateField('label_type', val ?? '')
            "
        />

        <!-- Note type filter (from controlled list) -->
        <Select
            v-if="showNoteTypeDropdown"
            :model-value="condition.note_type"
            :options="options.note_types"
            option-label="label"
            option-value="value"
            :placeholder="anyTypePlaceholder"
            show-clear
            class="facet-sub-dropdown"
            @update:model-value="
                (val: string | undefined) => updateField('note_type', val ?? '')
            "
        />

        <!-- Language filter for label/note facets -->
        <Select
            v-if="showLanguageDropdown"
            :model-value="condition.language"
            :options="options.languages"
            option-label="name"
            option-value="code"
            :placeholder="anyLanguagePlaceholder"
            show-clear
            class="facet-sub-dropdown"
            @update:model-value="(val: string) => updateField('language', val)"
        />

        <!-- Language facet (standalone) -->
        <Select
            v-if="showLanguageSelect"
            :model-value="condition.value as string"
            :options="options.languages"
            option-label="name"
            option-value="code"
            :placeholder="selectLanguagePlaceholder"
            class="facet-value-input"
            @update:model-value="(val: string) => updateField('value', val)"
        />

        <!-- Scheme facet -->
        <Select
            v-if="showSchemeSelect"
            :model-value="condition.value as string"
            :options="schemeDisplayOptions"
            option-label="label"
            option-value="id"
            :placeholder="selectSchemePlaceholder"
            class="facet-value-input"
            @update:model-value="(val: string) => updateField('value', val)"
        />

        <!-- Top concept facet: optionally filter by scheme -->
        <Select
            v-if="showTopConceptSchemeSelect"
            :model-value="condition.value as string"
            :options="schemeDisplayOptions"
            option-label="label"
            option-value="id"
            :placeholder="anyScheme"
            :show-clear="true"
            class="facet-value-input"
            @update:model-value="
                (val: string | undefined) => updateField('value', val ?? '')
            "
        />

        <!-- Lifecycle state facet -->
        <Select
            v-if="showLifecycleSelect"
            :model-value="condition.value as string"
            :options="options.lifecycle_states"
            option-label="name"
            option-value="id"
            :placeholder="selectStatePlaceholder"
            class="facet-value-input"
            @update:model-value="(val: string) => updateField('value', val)"
        />

        <!-- Concept set facet -->
        <Select
            v-if="showConceptSetSelect"
            :model-value="condition.value as string"
            :options="conceptSets"
            option-label="name"
            option-value="id"
            :placeholder="selectConceptSetPlaceholder"
            class="facet-value-input"
            @update:model-value="
                (val: string) => updateField('value', String(val))
            "
        />

        <Select
            v-if="showSourcePicker"
            :model-value="condition.value as string"
            :options="sourceSearchResults"
            option-label="display_value"
            option-value="resource_id"
            :filter="true"
            :filter-fields="['display_value', 'resource_id']"
            :empty-filter-message="noSourcesFoundMessage"
            :filter-placeholder="searchSourcesFilterPlaceholder"
            :loading="isLoadingSources"
            :placeholder="selectSourcePlaceholder"
            :show-clear="true"
            class="facet-value-input"
            @filter="onSourceFilter"
            @before-show="loadSources()"
            @update:model-value="
                (val: string | null) => updateField('value', val ?? '')
            "
        />

        <Select
            v-if="showContributorPicker"
            :model-value="condition.value as string"
            :options="contributorSearchResults"
            option-label="display_value"
            option-value="resource_id"
            :filter="true"
            :filter-fields="['display_value', 'resource_id']"
            :empty-filter-message="noContributorsFoundMessage"
            :filter-placeholder="searchContributorsFilterPlaceholder"
            :loading="isLoadingContributors"
            :placeholder="selectContributorPlaceholder"
            :show-clear="true"
            class="facet-value-input"
            @filter="onContributorFilter"
            @before-show="loadContributors()"
            @update:model-value="
                (val: string | null) => updateField('value', val ?? '')
            "
        />

        <!-- Concept type facet (from controlled list) -->
        <Select
            v-if="showConceptTypeDropdown"
            :model-value="condition.value as string"
            :options="options.concept_types"
            option-label="label"
            option-value="value"
            :placeholder="selectConceptTypePlaceholder"
            show-clear
            class="facet-value-input"
            @update:model-value="
                (val: string | undefined) => updateField('value', val ?? '')
            "
        />

        <!-- Direction for hierarchical relationships -->
        <Select
            v-if="showDirectionSelect"
            :model-value="condition.direction || 'broader'"
            :options="hierarchyDirections"
            option-label="label"
            option-value="value"
            class="facet-sub-dropdown"
            @update:model-value="(val: string) => updateField('direction', val)"
        />

        <!-- Cascade toggle for hierarchical relationships -->
        <ToggleButton
            v-if="showCascadeToggle"
            :model-value="!!condition.cascade"
            :on-label="$gettext('Include all')"
            :off-label="$gettext('Direct only')"
            class="cascade-toggle"
            :class="{ 'cascade-active': condition.cascade }"
            @update:model-value="toggleCascade"
        />

        <Button
            icon="pi pi-times"
            severity="danger"
            :text="true"
            :rounded="true"
            :aria-label="removeConditionLabel"
            @click="$emit('remove')"
        />
    </div>
</template>

<style scoped>
.facet-row {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    padding: 0.375rem 0;
    flex-wrap: wrap;
    font-family: var(--p-lingo-font-family);
}

.negation-toggle {
    flex: 0 0 auto;
    min-width: 3rem;
}

.negation-toggle :deep(.p-togglebutton) {
    font-size: var(--p-lingo-font-size-xsmall);
    font-weight: var(--p-lingo-font-weight-normal);
    border-radius: 0.125rem;
    padding: 0.25rem 0.5rem;
}

.negation-active :deep(.p-togglebutton) {
    background: var(--p-red-100) !important;
    color: var(--p-red-700) !important;
    border-color: var(--p-red-300) !important;
}

:global(.arches-dark) .negation-active :deep(.p-togglebutton) {
    background: var(--p-red-900) !important;
    color: var(--p-red-200) !important;
    border-color: var(--p-red-700) !important;
}

.facet-type-dropdown {
    min-width: 12rem;
    flex: 0 0 auto;
}

.match-mode-dropdown {
    min-width: 9rem;
    flex: 0 0 auto;
}

.facet-value-input {
    flex: 1 1 12rem;
    min-width: 8rem;
}

.facet-sub-dropdown {
    min-width: 10rem;
    flex: 0 0 auto;
}

.facet-row :deep(.p-select),
.facet-row :deep(.p-inputtext) {
    border-radius: 0.125rem;
    font-size: var(--p-lingo-font-size-smallnormal);
}

.facet-row :deep(.p-button) {
    border-radius: 0.125rem;
    font-size: var(--p-lingo-font-size-small);
}

.concept-hierarchy {
    font-size: small;
    color: var(--p-primary-500);
}

.cascade-toggle {
    flex: 0 0 auto;
}

.cascade-toggle :deep(.p-togglebutton) {
    font-size: var(--p-lingo-font-size-xsmall);
    font-weight: var(--p-lingo-font-weight-normal);
    border-radius: 0.125rem;
    padding: 0.25rem 0.5rem;
}

.cascade-active :deep(.p-togglebutton) {
    background: var(--p-primary-100) !important;
    color: var(--p-primary-700) !important;
    border-color: var(--p-primary-300) !important;
}

:global(.arches-dark) .cascade-active :deep(.p-togglebutton) {
    background: var(--p-primary-900) !important;
    color: var(--p-primary-200) !important;
    border-color: var(--p-primary-700) !important;
}
</style>
