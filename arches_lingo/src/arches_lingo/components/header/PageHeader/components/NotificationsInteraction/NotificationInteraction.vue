<script setup lang="ts">
import { ref } from "vue";
import { useGettext } from "vue3-gettext";

import Button from "primevue/button";
import NotificationsPanel from "@/arches_lingo/components/header/PageHeader/components/NotificationsInteraction/components/NotificationsPanel.vue";

const { $gettext } = useGettext();

const shouldShowNotificationsPanel = ref(false);

function activateHierarchyOverlay() {
    shouldShowNotificationsPanel.value = true;
}
</script>

<template>
    <div>
        <Button
            icon="pi pi-bell"
            variant="text"
            class="notifications-button"
            :label="$gettext('Notifications')"
            @click="activateHierarchyOverlay"
        />
        <NotificationsPanel
            v-model:should-show-notifications-panel="
                shouldShowNotificationsPanel
            "
        />
    </div>
</template>

<style scoped>
.notifications-button {
    color: var(--p-menubar-text-color) !important;
    height: 3rem;
}

.notifications-button:hover {
    background: var(--p-button-primary-hover-background) !important;
}
</style>
