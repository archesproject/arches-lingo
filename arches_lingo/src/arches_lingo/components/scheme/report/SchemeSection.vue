<script setup lang="ts">
import { useGettext } from "vue3-gettext";
import Button from "primevue/button";
import { OPEN_EDITOR } from "@/arches_lingo/constants.ts";

defineEmits([OPEN_EDITOR]);

const { $gettext } = useGettext();
const props = defineProps<{
    titleText: string;
}>();
</script>

<template>
    <div class="section">
        <div class="header">
            <h3>{{ props.titleText }}</h3>
            <div>
                <Button
                    :label="$gettext(`Add ${props.titleText}`)"
                    @click="$emit(OPEN_EDITOR)"
                ></Button>
            </div>
        </div>
        <div class="content">
            <slot></slot>
        </div>
    </div>
</template>

<style scoped>
.section {
    margin: 0 1rem;
}
.section .header {
    display: flex;
    align-items: center;
    border-bottom: 1px solid var(--p-menubar-border-color);
}
.section .header h3 {
    flex: 1;
}
.content {
    margin: 1rem 0;
}
</style>
