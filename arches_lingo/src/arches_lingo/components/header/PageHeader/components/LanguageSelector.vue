<script setup lang="ts">
import { inject, useTemplateRef } from "vue";
import { useGettext } from "vue3-gettext";

import Button from "primevue/button";
import Popover from "primevue/popover";
import RadioButton from 'primevue/radiobutton';

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
        >
            <div class="popover-header">
                <h4 class="header-title">
                    {{ $gettext("Language Selection") }}
                </h4>
                <div class="formats-container">
     
                    <!-- TODO: export format selection goes here -->
                    <div>
                        <div class="selection">
                            <RadioButton v-model="language" inputId="format4" name="zh" value="Chinese" />
                            <label for="language1">Chinese (zh)</label>
                        </div>
                        <div class="selection">
                            <RadioButton v-model="language" inputId="format1" name="en" value="English" />
                            <label for="language2">English (en)</label>
                        </div>
                        <div class="selection">
                            <RadioButton v-model="language" inputId="format2" name="de" value="German" />
                            <label for="languaget3">German (de)</label>
                        </div>
                        <div class="selection">
                            <RadioButton v-model="language" inputId="format3" name="es" value="Spanish" />
                            <label for="language4">Spanish (es)</label>
                        </div>
                    </div>
                </div>
            </div>
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

.p-popover-content {
    padding: 0rem;
}

.popover-header {
    font-family:'Lucida Sans', 'Lucida Sans Regular', 'Lucida Grande', 'Lucida Sans Unicode', Geneva, Verdana, sans-serif;
    padding: 0.5rem 0.5rem;
}

.header-title {
    margin: 0rem 0rem .5rem 0rem;
    padding-bottom: .5rem;
    border-bottom: 1px solid var(--p-header-toolbar-border);
}

.selection {
    display: flex;
    gap: .5rem;
    padding: .2rem;
    font-size: var(--p-lingo-font-size-smallnormal);
    align-items: center;
    color: var(--p-list-option-icon-color);
}
</style>
