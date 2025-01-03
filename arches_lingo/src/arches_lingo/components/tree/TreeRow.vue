<script setup lang="ts">
import { inject } from "vue";

import { getItemLabel } from "@/arches_vue_utils/utils.ts";
import {
    selectedLanguageKey,
    systemLanguageKey,
} from "@/arches_lingo/constants.ts";

import type { Language } from "@/arches_vue_utils/types";
import type { Ref } from "vue";
import type { TreeNode } from "primevue/treenode";
import type { Concept, Scheme } from "@/arches_lingo/types";

const { node, focusLabel, unfocusLabel } = defineProps<{
    node: TreeNode;
    focusLabel: string;
    unfocusLabel: string;
}>();
const selectedLanguage = inject(selectedLanguageKey) as Ref<Language>;
const systemLanguage = inject(systemLanguageKey) as Language;

const filterValue = defineModel<string>("filterValue");
const focusedNode = defineModel<TreeNode | null>("focusedNode");

const rowLabel = (data: Concept | Scheme) => {
    if (!data) {
        return "";
    }
    const unstyledLabel = getItemLabel(
        data,
        selectedLanguage?.value.code,
        systemLanguage.code,
    ).value;
    if (!filterValue.value) {
        return unstyledLabel;
    }
    const regex = new RegExp(`(${filterValue.value})`, "gi");
    return unstyledLabel.replace(regex, "<b>$1</b>");
};

const iconForFocusToggle = (node: TreeNode) => {
    return focusedNode.value?.data?.id === node.data.id
        ? "fa fa-search-minus"
        : "fa fa-bullseye";
};

const labelForFocusToggle = (node: TreeNode) => {
    return focusedNode.value?.data?.id === node.data.id
        ? unfocusLabel
        : focusLabel;
};

const toggleFocus = (node: TreeNode) => {
    if (focusedNode.value?.data?.id === node.data.id) {
        focusedNode.value = null;
    } else {
        focusedNode.value = node;
    }
};
</script>

<template>
    <!-- eslint-disable vue/no-v-html -->
    <span v-html="rowLabel(node.data)" />
    <!-- eslint-enable vue/no-v-html -->
    <i
        v-tooltip="{
            value: labelForFocusToggle(node),
            pt: { text: { style: { fontFamily: 'sans-serif' } } },
        }"
        role="button"
        :class="iconForFocusToggle(node)"
        :aria-label="labelForFocusToggle(node)"
        tabindex="0"
        :style="{ alignSelf: 'center', marginLeft: '1rem' }"
        @click="toggleFocus(node)"
        @keyup.enter="toggleFocus(node)"
    />
</template>
