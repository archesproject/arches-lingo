<script setup lang="ts">
import type { ResourceInstanceReference } from "@/arches_lingo/types";

const props = defineProps<{ value?: ResourceInstanceReference[] }>();
</script>
<template>
    <div v-if="props.value">
        <div
            v-for="val in props.value"
            :key="val.resourceXresourceId"
        >
            {{ val.display_value }}
        </div>
    </div>
</template>
