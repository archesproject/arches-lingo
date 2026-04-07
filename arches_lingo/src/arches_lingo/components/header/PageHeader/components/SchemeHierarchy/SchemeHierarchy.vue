<script setup lang="ts">
import { onMounted, provide, ref } from "vue";
import { storeToRefs } from "pinia";

import { useGettext } from "vue3-gettext";
import { useToast } from "primevue/usetoast";

import Button from "primevue/button";
import Tab from "primevue/tab";
import TabList from "primevue/tablist";
import Tabs from "primevue/tabs";

import ConceptTree from "@/arches_lingo/components/tree/ConceptTree.vue";
import ConceptSetBrowser from "@/arches_lingo/components/concept-set-browser/ConceptSetBrowser.vue";

import { fetchResourceInstanceLifecycleStates } from "@/arches_lingo/api.ts";

import { ERROR, DEFAULT_ERROR_TOAST_LIFE } from "@/arches_lingo/constants.ts";

import { useConceptStore } from "@/arches_lingo/stores/useConceptStore.ts";
import { useUserStore } from "@/arches_lingo/stores/useUserStore.ts";

const props = withDefaults(
    defineProps<{
        isOpen?: boolean;
    }>(),
    {
        isOpen: true,
    },
);

const { $gettext } = useGettext();
const toast = useToast();

const conceptStore = useConceptStore();
const { isAnonymous } = storeToRefs(useUserStore());

const conceptTreeKey = ref(0);
const resourceInstanceLifecycleStates = ref();
const activeTabValue = ref("hierarchies");

const emit = defineEmits<{
    (e: "shouldShowHierarchy", value: boolean): void;
}>();

provide("resourceInstanceLifecycleStates", resourceInstanceLifecycleStates);

onMounted(async () => {
    try {
        const [, fetchedResourceInstanceLifecycleStates] = await Promise.all([
            conceptStore.initialize(),
            fetchResourceInstanceLifecycleStates(),
        ]);

        resourceInstanceLifecycleStates.value =
            fetchedResourceInstanceLifecycleStates;
    } catch (error) {
        toast.add({
            severity: ERROR,
            life: DEFAULT_ERROR_TOAST_LIFE,
            summary: $gettext("Unable to fetch concepts"),
            detail: (error as Error).message,
        });
    }
});
</script>

<template>
    <div class="scheme-hierarchy">
        <div class="hierarchy-header-container">
            <Tabs
                v-model:value="activeTabValue"
                class="hierarchy-tabs"
            >
                <TabList>
                    <Tab value="hierarchies">
                        {{ $gettext("Explore Hierarchies") }}
                    </Tab>
                    <Tab
                        v-if="!isAnonymous"
                        value="sets"
                    >
                        {{ $gettext("Concept Sets") }}
                    </Tab>
                </TabList>
            </Tabs>
            <Button
                icon="pi pi-times"
                rounded
                text
                severity="contrast"
                :aria-label="$gettext('Close')"
                @click="emit('shouldShowHierarchy', false)"
            />
        </div>
        <div class="hierarchy-content">
            <ConceptTree
                v-show="activeTabValue === 'hierarchies'"
                :key="conceptTreeKey"
                :is-open="props.isOpen"
            />
            <ConceptSetBrowser
                v-if="!isAnonymous"
                v-show="activeTabValue === 'sets'"
            />
        </div>
    </div>
</template>

<style scoped>
.scheme-hierarchy {
    height: 100%;
    display: flex;
    flex-direction: column;
}

.hierarchy-header-container {
    display: flex;
    align-items: stretch;
    background: var(--p-header-toolbar-background);
    flex-shrink: 0;
}

.hierarchy-header-container :deep(.hierarchy-tabs) {
    flex: 1;
    min-width: 0;
}

.hierarchy-header-container :deep(.p-tablist) {
    background: var(--p-header-toolbar-background);
}

.hierarchy-header-container :deep(.p-tablist-tab-list) {
    border-color: var(--p-header-toolbar-border);
}

.hierarchy-header-container :deep(.p-tab) {
    color: var(--p-header-item-label);
}

.hierarchy-header-container :deep(.p-tab-active) {
    color: var(--p-primary-color);
}

.hierarchy-header-container
    :deep(.p-tab:not(.p-tab-active):not(.p-disabled):hover) {
    color: var(--p-text-color);
}

.hierarchy-content {
    flex: 1 1 auto;
    min-height: 0;
    overflow: hidden;
    display: flex;
    flex-direction: column;
}
</style>
