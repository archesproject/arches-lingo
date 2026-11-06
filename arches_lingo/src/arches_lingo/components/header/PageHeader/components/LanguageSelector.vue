<script setup lang="ts">
import { computed, ref, useTemplateRef } from "vue";
import { useGettext } from "vue3-gettext";
import { storeToRefs } from "pinia";

import Button from "primevue/button";
import Popover from "primevue/popover";
import RadioButton from "primevue/radiobutton";

import { useLanguageStore } from "@/arches_lingo/stores/useLanguageStore.ts";

import type { PopoverMethods } from "primevue/popover";

const { $gettext } = useGettext();

const languageStore = useLanguageStore();
const { selectedLanguage, availableLanguages } = storeToRefs(languageStore);

const popover = useTemplateRef<PopoverMethods>("popover");
const isLanguageSelectorVisible = ref(false);

const selectedCode = computed({
    get: () => selectedLanguage.value.code,
    set: (code: string) => {
        const lang = availableLanguages.value.find(
            (language) => language.code === code,
        );
        if (lang) {
            languageStore.setSelectedLanguage(lang);
        }
    },
});

const showSelector = computed(() => availableLanguages.value.length > 1);

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
            aria-haspopup="dialog"
            :aria-expanded="isLanguageSelectorVisible"
            @click="openLanguageSelector"
        >
            <div class="language-abbreviation-circle">
                {{ selectedLanguage.code }}
            </div>
            <span :lang="selectedLanguage.code">{{
                selectedLanguage.name
            }}</span>
        </Button>

        <Popover
            ref="popover"
            @show="isLanguageSelectorVisible = true"
            @hide="isLanguageSelectorVisible = false"
        >
            <fieldset class="popover-header">
                <legend class="header-title">
                    {{ $gettext("Language Selection") }}
                </legend>
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
                            name="ui-language"
                            :value="language.code"
                            :pt="{
                                input: {
                                    autofocus: language.code === selectedCode,
                                },
                            }"
                        />
                        <label :for="`language-${language.code}`">
                            <span :lang="language.code">{{
                                language.name
                            }}</span>
                            ({{ language.code }})
                        </label>
                    </span>
                </div>
            </fieldset>
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
    background: var(--p-lingo-navigation-bar-hover-background) !important;
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
    margin: 0;
    border: none;
    min-inline-size: 0;
}

.header-title {
    width: 100%;
    margin: 0rem 0rem 0.5rem 0rem;
    padding: 0 0 0.5rem 0;
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
