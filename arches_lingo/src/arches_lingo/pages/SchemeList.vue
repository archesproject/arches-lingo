<script setup lang="ts">
import { onMounted, ref } from "vue";
import SchemeCard from "@/arches_lingo/components/scheme/SchemeCard.vue";
import { fetchSchemes } from "@/arches_lingo/api.ts";

import type { SchemeResource } from "@/arches_lingo/types";

const schemes = ref<SchemeResource[]>([]);

onMounted(async () => {
    schemes.value = await fetchSchemes();
    schemes.value.unshift({
        resourceinstanceid: "placeholder-id",
        descriptors: {
            en: {
                name: "Create a new scheme",
                description: "This is a placeholder to create a new scheme",
            },
        },
    } as SchemeResource);
});
</script>

<template>
    <div>
        <ul class="scheme-cards">
            <li
                v-for="scheme in schemes"
                :key="scheme.resourceinstanceid"
            >
                <SchemeCard :scheme="scheme" />
            </li>
        </ul>
    </div>
</template>

<style scoped>
.scheme-cards {
    display: flex;
    flex-wrap: wrap;
    list-style-type: none;
    padding: 0;
}
</style>
