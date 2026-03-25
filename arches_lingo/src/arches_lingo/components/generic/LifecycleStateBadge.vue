<script setup lang="ts">
import { computed } from "vue";

import Tag from "primevue/tag";

import {
    DRAFT_LIFECYCLE_STATE_ID,
    EDITING_LIFECYCLE_STATE_ID,
    PUBLISHED_LIFECYCLE_STATE_ID,
    RETIRED_LIFECYCLE_STATE_ID,
} from "@/arches_lingo/constants.ts";

const props = defineProps<{
    lifecycleStateId?: string | null;
    lifecycleStateName?: string | null;
}>();

type TagSeverity =
    | "success"
    | "info"
    | "warn"
    | "danger"
    | "secondary"
    | "contrast";

const SEVERITY_BY_STATE_ID: Record<string, TagSeverity> = {
    [DRAFT_LIFECYCLE_STATE_ID]: "secondary",
    [EDITING_LIFECYCLE_STATE_ID]: "warn",
    [PUBLISHED_LIFECYCLE_STATE_ID]: "success",
    [RETIRED_LIFECYCLE_STATE_ID]: "danger",
};

const severity = computed<TagSeverity>(() => {
    if (!props.lifecycleStateId) return "secondary";
    return SEVERITY_BY_STATE_ID[props.lifecycleStateId] ?? "secondary";
});

const shouldRender = computed(
    () => Boolean(props.lifecycleStateId) && Boolean(props.lifecycleStateName),
);
</script>

<template>
    <Tag
        v-if="shouldRender"
        :value="lifecycleStateName!"
        :severity="severity"
        class="lifecycle-state-badge"
    />
</template>

<style scoped>
.lifecycle-state-badge {
    display: inline-flex;
    align-items: center;
    font-size: var(--p-lingo-font-size-xxsmall);
    padding: 0.25rem 0.75rem;
    border-radius: 1rem;
    white-space: nowrap;
}
</style>
