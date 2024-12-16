<script setup lang="ts">
import { useGettext } from "vue3-gettext";
import type { ResourceInstanceReference } from "@/arches_lingo/types";
import arches from "arches";

const { $gettext } = useGettext();

withDefaults(defineProps<{ value?: ResourceInstanceReference[] }>(), {
    value: (): ResourceInstanceReference[] => [],
});
</script>
<template>
    <span v-if="value">
        <span
            v-for="val in value"
            :key="val.resourceXresourceId"
            class="resource-instance-relationship-view"
        >
            <a :href="`${arches.urls.resource_editor}${val.resourceId}`">
                {{ val.display_value }}
            </a>
        </span>
    </span>
    <span v-else>{{ $gettext("None") }}</span>
</template>
