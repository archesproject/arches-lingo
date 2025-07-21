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
                    backgroundColor: 'var(--p-header-toolbar-background)',
                    borderBottom: '0.0625rem solid var(--p-header-toolbar-border)',
                    padding: '0.25rem 0.75rem',
                    fontFamily: 'var(--p-lingo-font-family)',
                },
            },
        }"
    >
         <div class="notifications-container">
            HELLO FROM THE HELP PANEL
        </div>
    </Drawer>
</template>

<style scoped>
.notifications-container {
    padding: .5rem .75rem;
}

</style>
