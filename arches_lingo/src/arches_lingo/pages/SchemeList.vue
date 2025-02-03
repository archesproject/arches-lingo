<script setup lang="ts">
import { onMounted, ref } from "vue";
import { useGettext } from "vue3-gettext";

import { useToast } from "primevue/usetoast";
import {
    DEFAULT_ERROR_TOAST_LIFE,
    ERROR,
} from "@/arches_references/constants.ts";

import SchemeCard from "@/arches_lingo/components/scheme/SchemeCard.vue";
import { fetchLingoResources } from "@/arches_lingo/api.ts";
import { NEW } from "@/arches_lingo/constants.ts";

import type { SchemeResource } from "@/arches_lingo/types";

const toast = useToast();
const { $gettext } = useGettext();

const schemes = ref<SchemeResource[]>([]);

onMounted(async () => {
    try {
        schemes.value = await fetchLingoResources("scheme");
    } catch (error) {
        toast.add({
            severity: ERROR,
            life: DEFAULT_ERROR_TOAST_LIFE,
            summary: $gettext("Unable to fetch schemes"),
            detail: error instanceof Error ? error.message : undefined,
        });
    }
    schemes.value.unshift({
        resourceinstanceid: NEW,
        descriptors: {},
    });
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
