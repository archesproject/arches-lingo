<script setup lang="ts">
    import { computed } from "vue"

    import type { TreeNode } from "primevue/treenode"

    const { node, focusLabel, unfocusLabel } = defineProps<{
        node: TreeNode,
        focusLabel: string,
        unfocusLabel: string,
    }>();

    const focusedNode = defineModel<TreeNode | null>("focusedNode");

    const isFocused = computed(() => {
        return focusedNode.value?.data?.id === node.data.id;
    });

    function toggleFocus() {
        if (isFocused.value) {
            focusedNode.value = null;
        } else {
            focusedNode.value = node;
        }
    }
</script>

<template>
    <i
        role="button"
        style="display: flex; align-items: center;"
        tabindex="0"
        v-tooltip="{
            value: isFocused ? unfocusLabel : focusLabel,
            pt: { 
                text: { 
                    style: { fontFamily: 'sans-serif' }
                } 
            }
        }"
        :aria-label="isFocused ? unfocusLabel : focusLabel"
        :class="isFocused ? 'fa fa-search-minus' : 'fa fa-bullseye'"
        @click="toggleFocus"
        @keyup.enter="toggleFocus"
    />
</template>
