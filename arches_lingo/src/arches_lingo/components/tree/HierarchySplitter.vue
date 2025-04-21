<script setup lang="ts">
import { onMounted, ref } from "vue";
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
</script>

<template>
    <div class="subheading">
        <Button
            :severity="SECONDARY"
            :label="$gettext('Toggle hierarchy')"
            @click="toggleShowHierarchy"
        />
    </div>
    <Splitter style="height: 100%; overflow: hidden">
        <SplitterPanel
            :size="30"
            :style="{
                flexDirection: 'column',
            }"
        >
            <ConceptTree />
        </SplitterPanel>
        <SplitterPanel
            :size="70"
            style="overflow-y: auto"
        >
            <RouterView :key="route.fullPath" />
        </SplitterPanel>
    </Splitter>
</template>

<style scoped>
.subheading {
    display: flex;
    padding: 0.5rem;
    gap: 0.5rem;
}

.subheading h2 {
    font-size: medium;
}
</style>
