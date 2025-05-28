<script setup lang="ts">
import { onMounted, provide, ref } from "vue";
import { useRoute } from "vue-router";
import { useGettext } from "vue3-gettext";

import Button from "primevue/button";
import Splitter from "primevue/splitter";
import SplitterPanel from "primevue/splitterpanel";

import { SECONDARY } from "@/arches_lingo/constants.ts";
import ConceptTree from "@/arches_lingo/components/tree/ConceptTree.vue";

const { $gettext } = useGettext();
const route = useRoute();

const showHierarchy = ref(false);
const conceptTreeKey = ref(0);

onMounted(() => {
    showHierarchy.value = Boolean(route.query.showHierarchy);
});

// vanilla JS instead of Vue Router to avoid reloading the page
function toggleShowHierarchy() {
    const url = new URL(window.location.href);

    if (showHierarchy.value) {
        url.searchParams.delete("showHierarchy");
        showHierarchy.value = false;
    } else {
        url.searchParams.set("showHierarchy", "true");
        showHierarchy.value = true;
    }

    window.history.replaceState({}, "", url);
}

function refreshConceptTree() {
    conceptTreeKey.value += 1;
}

provide("refreshConceptTree", refreshConceptTree);
</script>

<template>
    <div class="subheading">
        <Button
            class="toggle-hierarchy"
            :severity="SECONDARY"
            :label="$gettext('Toggle hierarchy')"
            @click="toggleShowHierarchy"
        />
    </div>
    <Splitter
        style="height: 100%; overflow: hidden; border-radius: 0"
        class="hierarchy-container"
        :pt="{
            gutter: {
                style: { display: showHierarchy ? 'flex' : 'none' },
            },
        }"
    >
        <SplitterPanel
            :size="40"
            :style="{
                display: showHierarchy ? 'flex' : 'none',
                flexDirection: 'column',
            }"
        >
            <ConceptTree :key="conceptTreeKey" />
        </SplitterPanel>
        <SplitterPanel
            :size="60"
            style="overflow-y: auto"
        >
            <RouterView :key="route.fullPath" />
        </SplitterPanel>
    </Splitter>
</template>

<style scoped>
.subheading {
    display: flex;
    margin: 0;
    gap: 0.5rem;
    height: 3rem;
    background: var(--p-button-secondary-background);
}

.subheading h2 {
    font-size: medium;
}

.toggle-hierarchy {
    border-radius: 0;
    border-inline-start: 0.06rem solid
        var(--p-button-secondary-active-border-color);
    border-inline-end: 0.06rem solid
        var(--p-button-secondary-active-border-color);
    font-size: 0.9rem;
}
</style>
