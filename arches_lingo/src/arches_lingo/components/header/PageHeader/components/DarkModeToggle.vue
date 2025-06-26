<script setup lang="ts">
import { ref } from "vue";
import { useGettext } from "vue3-gettext";

import { Theme } from "@primeuix/styled";
import ToggleButton from "primevue/togglebutton";

const { $gettext } = useGettext();

const darkModeClass = Theme.options.darkModeSelector.substring(1);
const isDarkModeEnabled = ref(
    document.documentElement.classList.contains(darkModeClass),
);

function toggleDarkMode() {
    document.documentElement.classList.toggle(darkModeClass);
    isDarkModeEnabled.value = !isDarkModeEnabled.value;
    localStorage.setItem(
        `arches.${darkModeClass}`,
        isDarkModeEnabled.value.toString(),
    );
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
