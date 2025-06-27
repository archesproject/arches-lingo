<script setup lang="ts">
import Drawer from "primevue/drawer";

const shouldShowNotificationsPanel = defineModel(
    "shouldShowNotificationsPanel",
    {
        type: Boolean,
        default: false,
    },
);
</script>

<template>
    <Drawer
        v-model:visible="shouldShowNotificationsPanel"
        position="right"
        style="min-width: 32rem"
        :header="$gettext('Notifications')"
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
        HELLO FROM THE NOTIFICATIONS PANEL
    </Drawer>
</template>

<style scoped></style>
