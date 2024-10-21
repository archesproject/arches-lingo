<script setup lang="ts">
import { ref } from "vue";
import { useGettext } from "vue3-gettext";

import ToggleButton from "primevue/togglebutton";

import { DEFAULT_THEME } from "@/arches/themes/default.ts";

const { $gettext } = useGettext();

const isDarkModeEnabled = ref(
    window.matchMedia &&
        window.matchMedia("(prefers-color-scheme: dark)").matches,
);

function toggleDarkMode() {
    const element = document.querySelector("html");
    // Remove the leading dot from the selector to get class name.
    element!.classList.toggle(
        DEFAULT_THEME.theme.options.darkModeSelector.substring(1),
    );
    isDarkModeEnabled.value = !isDarkModeEnabled.value;
}
</script>

<template>
    <ToggleButton
        :model-value="isDarkModeEnabled"
        :on-label="$gettext('Dark')"
        :off-label="$gettext('Light')"
        off-icon="pi pi-sun"
        on-icon="pi pi-moon"
        :pt="{
            root: { ariaLabel: $gettext('Toggle dark mode') },
            label: { style: { display: 'none' } },
        }"
        @click="toggleDarkMode"
    />
</template>
