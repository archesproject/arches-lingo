<script setup lang="ts">
    import type { TreeNode } from "primevue/treenode"
    
    const { node, addChildLabel } = defineProps<{
        node: TreeNode
        addChildLabel?: string
    }>()
    
    const emit = defineEmits<{ (e: "add-child", node: TreeNode): void }>()
    
    function onAddChild() {
        emit("add-child", node)
    }
</script>

<template>
    <i
        class="fa fa-plus"
        style="display: flex; align-items: center;"
        role="button"
        tabindex="0"
        v-tooltip="{
            value: addChildLabel,
            pt: { 
                text: { 
                    style: { fontFamily: 'sans-serif' } 
                } 
            }
        }"
        :aria-label="addChildLabel"
        @click="onAddChild"
        @keyup.enter="onAddChild"
    />
</template>