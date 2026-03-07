<script setup lang="ts">
import { computed, inject, ref, watch, type Ref } from "vue";
import { useGettext } from "vue3-gettext";

import Button from "primevue/button";
import InputText from "primevue/inputtext";
import Select from "primevue/select";
import ToggleButton from "primevue/togglebutton";

import { fetchConceptResources } from "@/arches_lingo/api.ts";
import {
    selectedLanguageKey,
    systemLanguageKey,
} from "@/arches_lingo/constants.ts";
import { getItemLabel } from "@/arches_controlled_lists/utils.ts";

import type { Label } from "@/arches_controlled_lists/types.ts";
import type { Language } from "@/arches_component_lab/types.ts";

import type {
    AdvancedSearchOptions,
    ConceptSetItem,
    FacetType,
    MatchMode,
    SchemeOption,
    SearchCondition,
} from "@/arches_lingo/types.ts";

const { $gettext } = useGettext();

const systemLanguage = inject(systemLanguageKey) as Language;
const selectedLanguage = inject(selectedLanguageKey) as Ref<Language>;

const props = defineProps<{
    condition: SearchCondition;
    options: AdvancedSearchOptions;
    conceptSets: ConceptSetItem[];
}>();

const emit = defineEmits<{
    (event: "update:condition", value: SearchCondition): void;
    (event: "remove"): void;
}>();

const facetTypes: { label: string; value: FacetType }[] = [
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
    { label: $gettext("URI"), value: "uri" },
    { label: $gettext("Identifier"), value: "identifier" },
    { label: $gettext("Lifecycle State"), value: "lifecycle_state" },
    { label: $gettext("Concept Set"), value: "concept_set" },
];

const matchModes: { label: string; value: MatchMode }[] = [
    { label: $gettext("Contains"), value: "contains" },
    { label: $gettext("Exact"), value: "exact" },
    { label: $gettext("Starts with"), value: "starts_with" },
    { label: $gettext("Ends with"), value: "ends_with" },
    { label: $gettext("Exists (any value)"), value: "exists" },
];

const hierarchyDirections = [
    { label: $gettext("Broader (parent of)"), value: "broader" },
    { label: $gettext("Narrower (child of)"), value: "narrower" },
];

const conceptSearchResults = ref<
    { display_value: string; resource_id: string }[]
>([]);
const isLoadingConcepts = ref(false);
let conceptSearchTimeout: ReturnType<typeof setTimeout> | null = null;

function onConceptFilter(event: { value: string }) {
    if (conceptSearchTimeout) {
        clearTimeout(conceptSearchTimeout);
    }
    conceptSearchTimeout = setTimeout(async () => {
        await loadConcepts(event.value);
    }, 400);
}

async function loadConcepts(term?: string) {
    try {
        isLoadingConcepts.value = true;
        const result = await fetchConceptResources(term || "", 50, 1);
        conceptSearchResults.value = (result.data || []).map(
            (item: { id: string; labels: Label[] }) => ({
                display_value:
                    getItemLabel(
                        item,
                        selectedLanguage.value.code,
                        systemLanguage.code,
                    ).value || item.id,
                resource_id: item.id,
            }),
        );
    } catch {
        conceptSearchResults.value = [];
    } finally {
        isLoadingConcepts.value = false;
    }
}

// Load initial concepts when a relationship facet is selected
watch(
    () => props.condition.facet,
    (facet) => {
        if (
            facet === "relationship_hierarchical" ||
            facet === "relationship_associated"
        ) {
            loadConcepts();
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

const schemeDisplayOptions = computed(() =>
    props.options.schemes.map((scheme: SchemeOption) => ({
        id: scheme.id,
        label: getItemLabel(
            scheme,
            selectedLanguage.value.code,
            systemLanguage.code,
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

const showMatchMode = computed(() => {
    return ["label", "note", "match_uri", "uri", "identifier"].includes(
        props.condition.facet,
    );
});

function updateField(field: keyof SearchCondition, value: string) {
    const updated = { ...props.condition, [field]: value };
    emit("update:condition", updated);
}

function updateFacet(facet: FacetType) {
    const updated: SearchCondition = {
        id: props.condition.id,
        facet,
        value: "",
    };
    emit("update:condition", updated);
}

function updateMatchMode(mode: MatchMode) {
    const updated = { ...props.condition, match_mode: mode };
    if (mode === "exists") {
        updated.value = "";
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

        <!-- Text input for label, note, URI, identifier, match_uri -->
        <InputText
            v-if="showValueInput"
            :model-value="condition.value"
            :placeholder="$gettext('Search text...')"
            class="facet-value-input"
            @update:model-value="
                (val: string | undefined) => updateField('value', val ?? '')
            "
        />

        <!-- Concept picker for hierarchical and associated relationships -->
        <Select
            v-if="showConceptPicker"
            :model-value="condition.value"
            :options="conceptSearchResults"
            option-label="display_value"
            option-value="resource_id"
            :filter="true"
            :filter-fields="['display_value', 'resource_id']"
            :empty-filter-message="$gettext('No concepts found')"
            :filter-placeholder="$gettext('Search concepts...')"
            :loading="isLoadingConcepts"
            :placeholder="$gettext('Select concept...')"
            :show-clear="true"
            class="facet-value-input"
            @filter="onConceptFilter"
            @before-show="loadConcepts()"
            @update:model-value="
                (val: string | null) => updateField('value', val ?? '')
            "
        />

        <!-- Label type filter (from controlled list) -->
        <Select
            v-if="showLabelTypeDropdown"
            :model-value="condition.label_type"
            :options="options.label_types"
            option-label="label"
            option-value="value"
            :placeholder="$gettext('Any type')"
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
            :placeholder="$gettext('Any type')"
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
            :placeholder="$gettext('Any language')"
            show-clear
            class="facet-sub-dropdown"
            @update:model-value="(val: string) => updateField('language', val)"
        />

        <!-- Language facet (standalone) -->
        <Select
            v-if="showLanguageSelect"
            :model-value="condition.value"
            :options="options.languages"
            option-label="name"
            option-value="code"
            :placeholder="$gettext('Select language')"
            class="facet-value-input"
            @update:model-value="(val: string) => updateField('value', val)"
        />

        <!-- Scheme facet -->
        <Select
            v-if="showSchemeSelect"
            :model-value="condition.value"
            :options="schemeDisplayOptions"
            option-label="label"
            option-value="id"
            :placeholder="$gettext('Select scheme')"
            class="facet-value-input"
            @update:model-value="(val: string) => updateField('value', val)"
        />

        <!-- Lifecycle state facet -->
        <Select
            v-if="showLifecycleSelect"
            :model-value="condition.value"
            :options="options.lifecycle_states"
            option-label="name"
            option-value="id"
            :placeholder="$gettext('Select state')"
            class="facet-value-input"
            @update:model-value="(val: string) => updateField('value', val)"
        />

        <!-- Concept set facet -->
        <Select
            v-if="showConceptSetSelect"
            :model-value="condition.value"
            :options="conceptSets"
            option-label="name"
            option-value="id"
            :placeholder="$gettext('Select concept set')"
            class="facet-value-input"
            @update:model-value="
                (val: string) => updateField('value', String(val))
            "
        />

        <!-- Concept type facet (from controlled list) -->
        <Select
            v-if="showConceptTypeDropdown"
            :model-value="condition.value"
            :options="options.concept_types"
            option-label="label"
            option-value="value"
            :placeholder="$gettext('Select concept type')"
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

        <Button
            icon="pi pi-times"
            severity="danger"
            text
            rounded
            :aria-label="$gettext('Remove condition')"
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
.facet-row :deep(.p-inputtext),
.facet-row :deep(.p-multiselect) {
    border-radius: 0.125rem;
    font-size: var(--p-lingo-font-size-smallnormal);
}

.facet-row :deep(.p-button) {
    border-radius: 0.125rem;
    font-size: var(--p-lingo-font-size-small);
}
</style>
