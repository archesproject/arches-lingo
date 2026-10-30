<script setup lang="ts">
import { computed, nextTick, ref, watch } from "vue";
import { useGettext } from "vue3-gettext";

import Button from "primevue/button";
import SelectButton from "primevue/selectbutton";

import FacetRow from "@/arches_lingo/components/advanced-search/FacetRow.vue";

import {
    focusFirstFocusableElement,
    generateConditionId,
} from "@/arches_lingo/utils.ts";

import type {
    AdvancedSearchOptions,
    ConceptSetItem,
    SearchCondition,
    SearchGroup,
    SearchOperator,
} from "@/arches_lingo/types.ts";

const { $gettext } = useGettext();

const props = defineProps<{
    group: SearchGroup;
    options: AdvancedSearchOptions;
    conceptSets: ConceptSetItem[];
    depth?: number;
    groupPosition?: string;
}>();

const emit = defineEmits<{
    (event: "update:group", value: SearchGroup): void;
    (event: "remove"): void;
}>();

const operatorOptions = computed(() => [
    { label: $gettext("AND"), value: "and" as SearchOperator },
    { label: $gettext("OR"), value: "or" as SearchOperator },
]);

const operatorLabel = computed(() =>
    props.groupPosition
        ? $gettext(
              "Group %{position}: combine conditions with",
              { position: props.groupPosition },
              true,
          )
        : $gettext("Combine conditions with"),
);

const groupName = computed(() => {
    const isMatchingAll = props.group.operator === "and";
    if (!props.groupPosition) {
        return isMatchingAll
            ? $gettext("Search conditions, match all")
            : $gettext("Search conditions, match any");
    }
    return isMatchingAll
        ? $gettext("Group %{position}, match all", {
              position: props.groupPosition,
          })
        : $gettext("Group %{position}, match any", {
              position: props.groupPosition,
          });
});

const groupConditionsRef = ref<HTMLElement | null>(null);
const addConditionButtonRef = ref<InstanceType<typeof Button> | null>(null);
let conditionIdToFocus: string | null = null;
let shouldFocusAddConditionButton = false;

watch(
    () => props.group.conditions,
    async () => {
        if (!conditionIdToFocus && !shouldFocusAddConditionButton) {
            return;
        }
        await nextTick();
        if (conditionIdToFocus) {
            focusFirstFocusableElement(
                groupConditionsRef.value?.querySelector<HTMLElement>(
                    `[data-condition-id="${conditionIdToFocus}"]`,
                ) ?? null,
            );
        } else {
            // @ts-expect-error This is an error in PrimeVue types
            addConditionButtonRef.value?.$el.focus();
        }
        conditionIdToFocus = null;
        shouldFocusAddConditionButton = false;
    },
);

const removeGroupLabel = computed(() =>
    $gettext("Remove group %{position}", {
        position: props.groupPosition ?? "",
    }),
);

function getChildPosition(index: number) {
    return props.groupPosition
        ? `${props.groupPosition}.${index + 1}`
        : String(index + 1);
}

function updateOperator(value: SearchOperator) {
    emit("update:group", { ...props.group, operator: value });
}

function addCondition() {
    const newCondition: SearchCondition = {
        id: generateConditionId(),
        facet: "label",
        value: "",
    };
    conditionIdToFocus = newCondition.id;
    emit("update:group", {
        ...props.group,
        conditions: [...props.group.conditions, newCondition],
    });
}

function addGroup() {
    const newGroup: SearchGroup = {
        id: generateConditionId(),
        operator: "and",
        conditions: [
            {
                id: generateConditionId(),
                facet: "label",
                value: "",
            } as SearchCondition,
        ],
    };
    conditionIdToFocus = newGroup.id;
    emit("update:group", {
        ...props.group,
        conditions: [...props.group.conditions, newGroup],
    });
}

function updateChild(index: number, updated: SearchCondition | SearchGroup) {
    const newConditions = [...props.group.conditions];
    newConditions[index] = updated;
    emit("update:group", { ...props.group, conditions: newConditions });
}

function removeChild(targetIndex: number) {
    const neighbour =
        props.group.conditions[targetIndex + 1] ??
        props.group.conditions[targetIndex - 1];
    conditionIdToFocus = neighbour?.id ?? null;
    shouldFocusAddConditionButton = !neighbour;
    const newConditions = props.group.conditions.filter(
        (_item, index) => index !== targetIndex,
    );
    emit("update:group", { ...props.group, conditions: newConditions });
}

function isGroup(item: SearchCondition | SearchGroup): item is SearchGroup {
    return "operator" in item;
}
</script>

<template>
    <div
        class="facet-group"
        :class="{ 'nested-group': (depth ?? 0) > 0 }"
        role="group"
        :aria-label="groupName"
    >
        <div class="group-header">
            <SelectButton
                :model-value="group.operator"
                :options="operatorOptions"
                option-label="label"
                option-value="value"
                :allow-empty="false"
                :aria-label="operatorLabel"
                class="operator-toggle"
                @update:model-value="updateOperator"
            />

            <div class="group-actions">
                <Button
                    ref="addConditionButtonRef"
                    :label="$gettext('Add Condition')"
                    icon="pi pi-plus"
                    size="small"
                    outlined
                    @click="addCondition"
                />
                <Button
                    :label="$gettext('Add Group')"
                    icon="pi pi-sitemap"
                    size="small"
                    outlined
                    @click="addGroup"
                />
                <Button
                    v-if="(depth ?? 0) > 0"
                    icon="pi pi-times"
                    severity="danger"
                    size="small"
                    text
                    rounded
                    :aria-label="removeGroupLabel"
                    @click="$emit('remove')"
                />
            </div>
        </div>

        <div
            ref="groupConditionsRef"
            class="group-conditions"
        >
            <template
                v-for="(child, index) in group.conditions"
                :key="child.id"
            >
                <div
                    v-if="index > 0"
                    class="operator-label"
                >
                    {{
                        group.operator === "and"
                            ? $gettext("AND")
                            : $gettext("OR")
                    }}
                </div>

                <FacetGroup
                    v-if="isGroup(child)"
                    :data-condition-id="child.id"
                    :group="child"
                    :options="options"
                    :concept-sets="conceptSets"
                    :depth="(depth ?? 0) + 1"
                    :group-position="getChildPosition(index)"
                    @update:group="updateChild(index, $event)"
                    @remove="removeChild(index)"
                />

                <FacetRow
                    v-else
                    :data-condition-id="child.id"
                    :condition="child"
                    :options="options"
                    :concept-sets="conceptSets"
                    :condition-position="getChildPosition(index)"
                    @update:condition="updateChild(index, $event)"
                    @remove="removeChild(index)"
                />
            </template>
        </div>
    </div>
</template>

<script lang="ts">
export default {
    name: "FacetGroup",
};
</script>

<style scoped>
.facet-group {
    padding: 0.75rem;
    background-color: var(--p-surface-card);
    font-family: var(--p-lingo-font-family);
}

.nested-group {
    border-color: var(--p-primary-200);
    background-color: var(--p-highlight-background);
    box-shadow: inset 0 0 0 0.125rem
        var(--p-lingo-query-builder-group-outline-color);
    margin: 0.25rem 0;
}

.group-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 0.5rem;
    gap: 0.5rem;
    flex-wrap: wrap;
}

.group-actions {
    display: flex;
    align-items: center;
    gap: 0.375rem;
}

.group-actions :deep(.p-button) {
    font-size: var(--p-lingo-font-size-xsmall);
    font-weight: var(--p-lingo-font-weight-normal);
    border-radius: 0.125rem;
}

.group-conditions {
    display: flex;
    flex-direction: column;
}

.operator-label {
    font-size: var(--p-lingo-font-size-xsmall);
    font-weight: var(--p-lingo-font-weight-normal);
    color: var(--p-lingo-accent-color);
    text-transform: uppercase;
    padding: 0.125rem 0.5rem;
    align-self: stretch;
    display: flex;
    align-items: center;
    gap: 0.5rem;
}

.operator-label::after {
    content: "";
    flex: 1;
    border-top: 0.0625rem solid var(--p-lingo-query-builder-rule-color);
}

.operator-toggle :deep(.p-selectbutton) {
    border-radius: 0.125rem;
}

.operator-toggle :deep(.p-togglebutton) {
    border-radius: 0.125rem;
    font-size: var(--p-lingo-font-size-xsmall);
}
</style>
