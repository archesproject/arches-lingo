<script setup lang="ts">
import { ref, watch } from "vue";
import { useGettext } from "vue3-gettext";

import SelectButton from "primevue/selectbutton";

import { Theme } from "@primeuix/styled";

const { $gettext } = useGettext();

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
        label: $gettext("Bright Mode"),
        value: false,
        disabled: false,
    },
    {
        icon: "pi pi-moon",
        label: $gettext("Dark Mode"),
        value: true,
        disabled: false,
    },
    {
        icon: "pi pi-users",
        label: $gettext("Accessible Mode"),
        value: "",
        disabled: true,
    },
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
    </div>
</template>

<style scoped>
.section-title {
    color: var(--p-text-muted-color);
    margin-bottom: 0.5rem;
}

.p-selectbutton {
    flex-direction: column;
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
}
</style>
