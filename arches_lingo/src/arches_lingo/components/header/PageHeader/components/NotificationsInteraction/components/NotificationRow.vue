<script setup lang="ts">
import { dismissNotifications } from "@/arches_lingo/api.ts";
import type { Notification } from "@/arches_lingo/types.ts";

const { notification } = defineProps<{
    notification: Notification;
}>();

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
            hour12: true,
        })
    );
}
</script>

<template>
    <span class="notification-item">
        <div class="date">{{ formatDate(notification.created) }}</div>
        <div>{{ notification.message }}</div>
    </span>
    <i
        v-if="notification.isread === false"
        class="pi pi-times"
        @click="dismissNotifications([notification.id])"
    ></i>
</template>

<style scoped>
.date {
    color: var(--p-search-result-color);
}
.notification-item {
    font-size: var(--p-lingo-font-size-small);
}
</style>
