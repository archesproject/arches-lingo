<script setup lang="ts">
import type { ControlledListItem } from "@/arches_lingo/types";

withDefaults(
    defineProps<{
        value?: ControlledListItem[] | ControlledListItem;
    }>(),
    {
        value: () => [],
    },
);
</script>
<template>
    <span v-if="value instanceof Array">
        <span
            v-for="val in value"
            :key="val.list_id"
        >
            <span>{{ val.labels[0].value }}</span>
        </span>
    </span>
    <span v-else-if="value">
        <span>{{ (value as ControlledListItem).labels[0].value }}</span>
    </span>
    <span v-else>
        <span>{{ $gettext("None") }}</span>
    </span>
</template>
