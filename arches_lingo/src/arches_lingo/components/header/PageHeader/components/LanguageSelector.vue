<script setup lang="ts">
import { inject, useTemplateRef } from "vue";
import { useGettext } from "vue3-gettext";

import Button from "primevue/button";
import Popover from "primevue/popover";

import { selectedLanguageKey } from "@/arches_lingo/constants.ts";

import type { PopoverMethods } from "primevue/popover";

const { $gettext } = useGettext();

const selectedLanguage = inject(selectedLanguageKey);

const popover = useTemplateRef<PopoverMethods>("popover");

function openLanguageSelector(event: MouseEvent) {
    popover.value!.toggle(event);
}
</script>

<template>
    <div style="display: flex; align-items: center; gap: 0.5rem">
        <Button
            :aria-label="$gettext('Open language selector')"
            @click="openLanguageSelector"
        >
            <div class="language-abbreviation-circle">
                {{ selectedLanguage?.code }}
            </div>
            <span>{{ selectedLanguage?.name }}</span>
        </Button>

        <Popover
            ref="popover"
            style="padding: 1rem 0.5rem"
        >
            HELLO FROM LANGUAGE SELECTOR
        </Popover>
    </div>
</template>

<style scoped>
.p-button {
    background: var(--p-menubar-background) !important;
    border: none !important;
    color: var(--p-menubar-text-color) !important;
}

.p-button:hover {
    background: var(--p-button-primary-hover-background) !important;
}
.language-abbreviation-circle {
    width: 2rem;
    height: 2rem;
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    background-color: var(--p-amber-800);
    border: 0.09rem solid var(--p-primary-950);
}
</style>
