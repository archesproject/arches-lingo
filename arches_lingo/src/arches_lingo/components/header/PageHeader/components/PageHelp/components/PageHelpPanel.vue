<script setup lang="ts">
import Drawer from "primevue/drawer";

const shouldShowPageHelpPanel = defineModel("shouldShowPageHelpPanel", {
    type: Boolean,
    default: false,
});
</script>

<template>
    <Drawer
        v-model:visible="shouldShowPageHelpPanel"
        position="right"
        style="min-width: 32rem"
        :header="$gettext('Help')"
        :pt="{
            content: {
                style: {
                    padding: '0',
                    display: 'flex',
                    flexDirection: 'column',
                    fontFamily: 'var(--p-lingo-font-family)',
                },
            },
            header: {
                style: {
                    display: 'flex',
                    justifyContent: 'space-between',
                    backgroundColor: 'var(--p-form-field-filled-background)',
                    paddingBottom: '0.5rem',
                    fontFamily: 'var(--p-lingo-font-family)',
                },
            },
        }"
    >
        HELLO FROM THE HELP PANEL
    </Drawer>
</template>

<style scoped></style>
