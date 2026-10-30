<script setup lang="ts">
import { useGettext } from "vue3-gettext";

import Button from "primevue/button";

import NotificationFileViewer from "@/arches_lingo/components/header/PageHeader/components/NotificationsInteraction/components/NotificationFileViewer.vue";
import NotificationLinkViewer from "@/arches_lingo/components/header/PageHeader/components/NotificationsInteraction/components/NotificationLinkViewer.vue";
import { dismissNotifications } from "@/arches_lingo/api.ts";
import type { Notification } from "@/arches_lingo/types.ts";

const { notification, showUnreadOnly } = defineProps<{
    notification: Notification;
    showUnreadOnly: boolean;
}>();

const { $gettext } = useGettext();

function formatDate(dateString: string): string {
    const date = new Date(dateString);
    return (
        date.toLocaleDateString(undefined, {
            weekday: "long",
            day: "2-digit",
            month: "long",
            year: "numeric",
        }) +
        " | " +
        date.toLocaleTimeString(undefined, {
            hour: "2-digit",
            minute: "2-digit",
        })
    );
}
</script>

<template>
    <div class="notification-item">
        <div class="date">{{ formatDate(notification.created) }}</div>
        <div class="message">{{ notification.message }}</div>
        <NotificationFileViewer
            v-for="file in notification.files"
            :key="file.fileid"
            :file="file"
        />
        <NotificationLinkViewer
            v-if="notification.link"
            :link="notification.link"
        />
    </div>
    <Button
        v-if="notification.isread === false && showUnreadOnly"
        class="dismiss-button"
        icon="pi pi-times"
        severity="danger"
        rounded
        size="small"
        :aria-label="$gettext('Dismiss notification')"
        @click="dismissNotifications([notification.id])"
    ></Button>
</template>

<style scoped>
.date {
    color: var(--p-search-result-color);
}
.message {
    text-overflow: ellipsis;
    margin-top: 0.5rem;
    margin-bottom: 0.25rem;
}
.notification-item {
    font-size: var(--p-lingo-font-size-small);
    padding-inline-end: 0.25rem;
}
.dismiss-button {
    flex-shrink: 0;
}
</style>
