<script setup lang="ts">
import { dismissNotifications } from "@/arches_lingo/api.ts";
import type { Notification } from "@/arches_lingo/types.ts";

const { notification } = defineProps<{
    notification: Notification;
}>();
</script>

<template>
    <span class="notification-item">
        {{ notification.message }}
    </span>
    <i
        class="pi pi-times"
        @click="dismissNotifications([notification.id])"
    ></i>
</template>

<style scoped>
.notification-item {
    font-size: var(--p-lingo-font-size-small);
}
</style>
