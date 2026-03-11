<script setup lang="ts">
import { computed } from "vue";
import { storeToRefs } from "pinia";
import { getItemLabel } from "@/arches_controlled_lists/utils.ts";
import { useLanguageStore } from "@/arches_lingo/stores/useLanguageStore.ts";
import type { TreeNode } from "primevue/treenode";

const { node, filterValue } = defineProps<{
    node: TreeNode;
    filterValue: string;
}>();

const { selectedLanguage, systemLanguage } = storeToRefs(useLanguageStore());

function tokenizeLabel(
    label: string,
    filter?: string,
): { text: string; highlight: boolean }[] {
    if (!filter) {
        return [{ text: label, highlight: false }];
    }

    const regex = new RegExp(`(${filter})`, "gi");
    const parts = label.split(regex);

    return parts.reduce<{ text: string; highlight: boolean }[]>((acc, part) => {
        if (part) {
            acc.push({
                text: part,
                highlight: part.toLowerCase() === filter.toLowerCase(),
            });
        }
        return acc;
    }, []);
}

const tokenizedLabel = computed(() => {
    if (!node.data) {
        return [];
    }

    const unstyledLabel = getItemLabel(
        node.data,
        selectedLanguage.value.code,
        systemLanguage.value.code,
    ).value;

    return tokenizeLabel(unstyledLabel, filterValue);
});
</script>

<template>
    <div>
        <template
            v-for="(token, index) in tokenizedLabel"
            :key="index"
        >
            <b v-if="token.highlight">{{ token.text }}</b>
            <span v-else>{{ token.text }}</span>
        </template>
    </div>
</template>
