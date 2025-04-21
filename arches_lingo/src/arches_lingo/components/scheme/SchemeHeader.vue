<script setup lang="ts">
import { inject, onMounted, ref } from "vue";
import { useGettext } from "vue3-gettext";

import { useToast } from "primevue/usetoast";
import Divider from "primevue/divider";
import {
    DEFAULT_ERROR_TOAST_LIFE,
    ERROR,
    systemLanguageKey,
} from "@/arches_lingo/constants.ts";

import { fetchLingoResource } from "@/arches_lingo/api.ts";
import { extractDescriptors } from "@/arches_lingo/utils.ts";

import type {
    DataComponentMode,
    ResourceInstanceResult,
    SchemeHeader,
} from "@/arches_lingo/types";
import type { Language } from "@/arches_vue_utils/types";

const toast = useToast();
const { $gettext } = useGettext();
const systemLanguage = inject(systemLanguageKey) as Language;

const props = defineProps<{
    mode: DataComponentMode;
    sectionTitle: string;
    componentName: string;
    graphSlug: string;
    resourceInstanceId: string;
    nodegroupAlias: string;
}>();

const scheme = ref<ResourceInstanceResult>();
const data = ref<SchemeHeader>();
const isLoading = ref(true);

function extractSchemeHeaderData(scheme: ResourceInstanceResult) {
    const name = scheme?.name;
    const descriptor = extractDescriptors(scheme, systemLanguage);
    // TODO: get human-readable user name from resource endpoint
    const principalUser = "Anonymous"; //scheme?.principalUser; // returns userid int
    // TODO: get human-readable life cycle state from resource endpoint
    const lifeCycleState = $gettext("Draft");

    data.value = {
        name: name,
        descriptor: descriptor,
        principalUser: principalUser,
        lifeCycleState: lifeCycleState,
    };
}

onMounted(async () => {
    try {
        scheme.value = await fetchLingoResource(
            props.graphSlug,
            props.resourceInstanceId,
        );

        extractSchemeHeaderData(scheme.value!);
    } catch (error) {
        toast.add({
            severity: ERROR,
            life: DEFAULT_ERROR_TOAST_LIFE,
            summary: $gettext("Unable to fetch scheme"),
            detail: error instanceof Error ? error.message : undefined,
        });
    } finally {
        isLoading.value = false;
    }
});
</script>

<template>
    <ProgressSpinner
        v-if="isLoading"
        style="width: 100%"
    />

    <div v-else>
        <div class="header-row">
            <h2>
                {{ data?.descriptor?.name }} ({{ data?.descriptor?.language }})
            </h2>
        </div>

        <div class="header-row">
            <!-- TODO: Life Cycle mgmt functionality goes here -->
            <div class="header-item">
                <span class="header-item-label">{{
                    $gettext("Life cycle state:")
                }}</span>
                <span>{{ data?.lifeCycleState }}</span>
            </div>
        </div>

        <div class="header-row">
            <div class="header-item">
                <span class="header-item-label">{{ $gettext("Owner:") }}</span>
                <span>{{ data?.principalUser || $gettext("Anonymous") }}</span>
            </div>
        </div>

        <Divider />
    </div>
</template>

<style scoped>
h2 {
    margin-bottom: 1rem;
}
.p-button-link {
    padding: 0;
    margin: 0;
}
.header-row {
    display: flex;
    justify-content: space-between;
    align-items: center;
}
.header-item {
    display: inline-flex;
    margin-inline-end: 1rem;
}
.header-item-label {
    font-weight: bold;
    margin-inline-end: 0.25rem;
}
</style>
