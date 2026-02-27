<script setup lang="ts">
import { computed } from "vue";
import { useGettext } from "vue3-gettext";

import Button from "primevue/button";
import Dropdown from "primevue/dropdown";
import InputText from "primevue/inputtext";

import type {
    AdvancedSearchOptions,
    ConceptSetItem,
    FacetType,
    SearchCondition,
} from "@/arches_lingo/types.ts";

const { $gettext } = useGettext();

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

const labelTypes = [
    { label: $gettext("Preferred Label"), value: "prefLabel" },
    { label: $gettext("Alternative Label"), value: "altLabel" },
    { label: $gettext("Hidden Label"), value: "hidden" },
];

const hierarchyDirections = [
    { label: $gettext("Broader (parent of)"), value: "broader" },
    { label: $gettext("Narrower (child of)"), value: "narrower" },
];

const showValueInput = computed(() => {
    const facet = props.condition.facet;
    return [
        "label",
        "note",
        "match_uri",
        "uri",
        "identifier",
        "relationship_hierarchical",
        "relationship_associated",
    ].includes(facet);
});

const showLabelTypeDropdown = computed(() => props.condition.facet === "label");

const showNoteTypeDropdown = computed(() => props.condition.facet === "note");

const showLanguageDropdown = computed(() =>
    ["label", "note"].includes(props.condition.facet),
);

const showLanguageSelect = computed(() => props.condition.facet === "language");

const showSchemeSelect = computed(() => props.condition.facet === "scheme");

const showLifecycleSelect = computed(
    () => props.condition.facet === "lifecycle_state",
);

const showConceptSetSelect = computed(
    () => props.condition.facet === "concept_set",
);

const showConceptTypeInput = computed(
    () => props.condition.facet === "concept_type",
);

const showDirectionSelect = computed(
    () => props.condition.facet === "relationship_hierarchical",
);

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
</script>

<template>
    <div class="facet-row">
        <Dropdown
            :model-value="condition.facet"
            :options="facetTypes"
            option-label="label"
            option-value="value"
            :placeholder="$gettext('Select facet')"
            class="facet-type-dropdown"
            @update:model-value="updateFacet"
        />

        <!-- Text input for label, note, URI, identifier, match_uri, relationships -->
        <InputText
            v-if="showValueInput"
            :model-value="condition.value"
            :placeholder="$gettext('Search text...')"
            class="facet-value-input"
            @update:model-value="
                (val: string | undefined) => updateField('value', val ?? '')
            "
        />

        <!-- Label type filter -->
        <Dropdown
            v-if="showLabelTypeDropdown"
            :model-value="condition.label_type"
            :options="labelTypes"
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

        <!-- Note type filter (placeholder — populated from options) -->
        <InputText
            v-if="showNoteTypeDropdown"
            :model-value="condition.note_type || ''"
            :placeholder="$gettext('Note type (optional)')"
            class="facet-sub-dropdown"
            @update:model-value="
                (val: string | undefined) => updateField('note_type', val ?? '')
            "
        />

        <!-- Language filter for label/note facets -->
        <Dropdown
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
        <Dropdown
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
        <Dropdown
            v-if="showSchemeSelect"
            :model-value="condition.value"
            :options="options.schemes"
            option-label="label"
            option-value="id"
            :placeholder="$gettext('Select scheme')"
            class="facet-value-input"
            @update:model-value="(val: string) => updateField('value', val)"
        />

        <!-- Lifecycle state facet -->
        <Dropdown
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
        <Dropdown
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

        <!-- Concept type facet (text input for list_item_id) -->
        <InputText
            v-if="showConceptTypeInput"
            :model-value="condition.value"
            :placeholder="$gettext('Concept type ID')"
            class="facet-value-input"
            @update:model-value="
                (val: string | undefined) => updateField('value', val ?? '')
            "
        />

        <!-- Direction for hierarchical relationships -->
        <Dropdown
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

.facet-type-dropdown {
    min-width: 12rem;
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
.facet-row :deep(.p-dropdown),
.facet-row :deep(.p-multiselect) {
    border-radius: 0.125rem;
    font-size: var(--p-lingo-font-size-smallnormal);
}

.facet-row :deep(.p-button) {
    border-radius: 0.125rem;
    font-size: var(--p-lingo-font-size-small);
}
</style>
