<script setup lang="ts">
import { ref, useId, watch } from "vue";
import { useGettext } from "vue3-gettext";

import SelectButton from "primevue/selectbutton";

import { Theme } from "@primeuix/styled";

import {
    HIGH_CONTRAST_CLASS,
    setHighContrast,
} from "@/arches_lingo/themes/high_contrast.ts";

const { $gettext } = useGettext();

const contrastLabelId = useId();

const darkModeClass = Theme.options.darkModeSelector.substring(1);
const isDarkModeEnabled = ref(
    document.documentElement.classList.contains(darkModeClass),
);
watch(
    isDarkModeEnabled,
    (newValue) => {
        setTheme(newValue);
    },
    { immediate: true },
);

const options = ref([
    {
        icon: "pi pi-sun",
        label: $gettext("Bright"),
        value: false,
        disabled: false,
    },
    {
        icon: "pi pi-moon",
        label: $gettext("Dark"),
        value: true,
        disabled: false,
    },
]);

const isHighContrastEnabled = ref(
    document.documentElement.classList.contains(HIGH_CONTRAST_CLASS),
);
watch(isHighContrastEnabled, setHighContrast);

const contrastOptions = ref([
    { label: $gettext("Off"), value: false },
    { label: $gettext("On"), value: true },
]);

function setTheme(value: boolean) {
    document.documentElement.classList.toggle(darkModeClass, value);
    isDarkModeEnabled.value = value;

    localStorage.setItem(
        `arches.${darkModeClass}`,
        isDarkModeEnabled.value.toString(),
    );
}
</script>

<template>
    <div>
        <div class="section-title">{{ $gettext("Theme") }}</div>

        <SelectButton
            v-model="isDarkModeEnabled"
            data-key="value"
            option-disabled="disabled"
            option-label="label"
            option-value="value"
            :allow-empty="false"
            :aria-label="$gettext('Theme Selector')"
            :options="options"
        >
            <template #option="slotProps">
                <i :class="slotProps.option.icon"></i>
                <span>{{ slotProps.option.label }}</span>
            </template>
        </SelectButton>

        <div
            :id="contrastLabelId"
            class="section-title contrast-title"
        >
            {{ $gettext("Increase Contrast") }}
        </div>

        <SelectButton
            v-model="isHighContrastEnabled"
            data-key="value"
            option-label="label"
            option-value="value"
            :allow-empty="false"
            :aria-labelledby="contrastLabelId"
            :options="contrastOptions"
        >
            <template #option="slotProps">
                <i
                    v-if="slotProps.option.value === isHighContrastEnabled"
                    class="pi pi-check"
                    aria-hidden="true"
                ></i>
                <span>{{ slotProps.option.label }}</span>
            </template>
        </SelectButton>
    </div>
</template>

<style scoped>
.section-title {
    color: var(--p-text-muted-color);
    margin-bottom: 0.5rem;
    font-weight: 300;
}

.contrast-title {
    margin-top: 1rem;
}

.p-selectbutton {
    color: var(--p-text-muted-color);
}

:deep(.p-selectbutton .p-togglebutton:first-child) {
    border-start-start-radius: 0;
    border-end-start-radius: 0;
}
:deep(.p-selectbutton .p-togglebutton:last-child) {
    border-start-end-radius: 0;
    border-end-end-radius: 0;
}

:deep(.p-togglebutton-content) {
    justify-content: flex-start;
    font-size: var(--p-lingo-font-size-xsmall);
}
</style>
