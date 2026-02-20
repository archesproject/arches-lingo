<script setup lang="ts">
import { computed, inject, useTemplateRef } from "vue";
import { useGettext } from "vue3-gettext";

import Button from "primevue/button";
import Popover from "primevue/popover";
import RadioButton from "primevue/radiobutton";

import {
    availableLanguagesKey,
    selectedLanguageKey,
} from "@/arches_lingo/constants.ts";

import type { PopoverMethods } from "primevue/popover";

const { $gettext } = useGettext();

const selectedLanguage = inject(selectedLanguageKey);
const availableLanguages = inject(availableLanguagesKey);

const popover = useTemplateRef<PopoverMethods>("popover");

const selectedCode = computed({
    get: () => selectedLanguage?.value?.code ?? "",
    set: (code: string) => {
        if (!selectedLanguage || !availableLanguages) return;
        const lang = availableLanguages.value.find((l) => l.code === code);
        if (lang) {
            selectedLanguage.value = lang;
        }
    },
});

const showSelector = computed(
    () => availableLanguages && availableLanguages.value.length > 1,
);

function openLanguageSelector(event: MouseEvent) {
    popover.value!.toggle(event);
}
</script>

<template>
    <div
        v-if="showSelector"
        class="language-selector"
    >
        <Button
            :aria-label="$gettext('Open language selector')"
            @click="openLanguageSelector"
        >
            <div class="language-abbreviation-circle">
                {{ selectedLanguage?.code }}
            </div>
            <span>{{ selectedLanguage?.name }}</span>
        </Button>

        <Popover ref="popover">
            <div class="popover-header">
                <h4 class="header-title">
                    {{ $gettext("Language Selection") }}
                </h4>
                <div class="formats-container">
                    <span
                        v-for="language in availableLanguages"
                        :key="language.code"
                        class="selection"
                    >
                        <RadioButton
                            :key="language.code"
                            v-model="selectedCode"
                            :input-id="`language-${language.code}`"
                            :value="language.code"
                        />
                        <label :for="`language-${language.code}`">
                            {{ language.name }} ({{ language.code }})
                        </label>
                    </span>
                </div>
            </div>
        </Popover>
    </div>
</template>

<style scoped>
.language-selector {
    display: flex;
    align-items: center;
    gap: 0.5rem;
}

.p-button {
    background: transparent !important;
    border: none !important;
    color: inherit !important;
    border-radius: 0;
    font-size: 0.875rem;
}

.p-button:hover {
    background: var(
        --p-button-text-hover-background,
        var(--p-button-primary-hover-background)
    ) !important;
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

.p-popover-content {
    padding: 0rem;
}

.popover-header {
    font-family: var(--p-lingo-font-family);
    padding: 0.5rem 0.5rem;
}

.header-title {
    margin: 0rem 0rem 0.5rem 0rem;
    padding-bottom: 0.5rem;
    border-bottom: 0.0625rem solid var(--p-header-toolbar-border);
    font-weight: 400;
}

.selection {
    display: flex;
    gap: 0.5rem;
    padding: 0.2rem 0.2rem 0.4rem 0.2rem;
    font-size: var(--p-lingo-font-size-small);
    align-items: center;
    color: var(--p-list-option-icon-color);
}
</style>
