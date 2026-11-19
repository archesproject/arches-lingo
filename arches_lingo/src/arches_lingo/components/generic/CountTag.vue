<script setup lang="ts">
import { useGettext } from "vue3-gettext";

import Tag from "primevue/tag";

const { count } = defineProps<{
    count: number;
}>();

const { $ngettext } = useGettext();
</script>

<template>
    <Tag severity="secondary">
        <span
            class="p-tag-label"
            aria-hidden="true"
            >{{ count }}</span
        >
        <span class="p-hidden-accessible">{{
            $ngettext("%{count} entry", "%{count} entries", count, {
                count: String(count),
            })
        }}</span>
    </Tag>
</template>
