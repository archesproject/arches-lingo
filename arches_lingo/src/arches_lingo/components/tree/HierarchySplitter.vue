<script setup lang="ts">
import { inject, provide, ref } from "vue";
import { useRouter } from "vue-router";
import { useGettext } from "vue3-gettext";

import Button from "primevue/button";
import ProgressSpinner from "primevue/progressspinner";
import Splitter from "primevue/splitter";
import SplitterPanel from "primevue/splitterpanel";

import { getItemLabel } from "@/arches_vue_utils/utils.ts";
import { shouldUseContrast } from "@/arches_references/utils.ts";
import {
    CONTRAST,
    SECONDARY,
    displayedRowKey,
    selectedLanguageKey,
    systemLanguageKey,
} from "@/arches_lingo/constants.ts";
import { routeNames } from "@/arches_lingo/routes.ts";
import { dataIsConcept, dataIsScheme } from "@/arches_lingo/utils.ts";
import ConceptTree from "@/arches_lingo/components/tree/ConceptTree.vue";

import type { Ref } from "vue";
import type { Language } from "@/arches_vue_utils/types";
import type { Concept, Scheme } from "@/arches_lingo/types";

const { $gettext } = useGettext();
const router = useRouter();
const selectedLanguage = inject(selectedLanguageKey) as Ref<Language>;
const systemLanguage = inject(systemLanguageKey) as Language;

const displayedRow: Ref<Concept | Scheme | null> = ref(null);
const setDisplayedRow = (val: Concept | Scheme | null) => {
    displayedRow.value = val;
    if (val === null) {
        return;
    }
    // TODO: Consider adding some sort of short-circuiting of fetchUser
    if (dataIsScheme(val)) {
        router.push({ name: routeNames.scheme, params: { id: val.id } });
    } else if (dataIsConcept(val)) {
        router.push({ name: routeNames.concept, params: { id: val.id } });
    }
};
// @ts-expect-error vue-tsc doesn't like arbitrary properties here
provide(displayedRowKey, { displayedRow, setDisplayedRow });

const showHierarchy = ref(false);
</script>

<template>
    <div class="subheading">
        <h2 v-if="displayedRow">
            {{
                getItemLabel(
                    displayedRow,
                    selectedLanguage.code,
                    systemLanguage.code,
                ).value
            }}
        </h2>
        <Button
            :severity="shouldUseContrast() ? CONTRAST : SECONDARY"
            :label="$gettext('Toggle hierarchy')"
            @click="() => (showHierarchy = !showHierarchy)"
        />
    </div>
    <Splitter
        style="height: 100%"
        :pt="{
            gutter: { style: { display: showHierarchy ? 'flex' : 'none' } },
        }"
    >
        <SplitterPanel
            :size="40"
            :min-size="25"
            :style="{
                display: showHierarchy ? 'flex' : 'none',
                flexDirection: 'column',
            }"
        >
            <Suspense>
                <ConceptTree />
                <template #fallback>
                    <ProgressSpinner />
                </template>
            </Suspense>
        </SplitterPanel>
        <SplitterPanel :min-size="25">
            <RouterView />
        </SplitterPanel>
    </Splitter>
</template>

<style scoped>
.subheading {
    display: flex;
    margin: 0.5rem;
    gap: 0.5rem;
}

.subheading h2 {
    font-size: medium;
}
</style>
