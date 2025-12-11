<script setup lang="ts">
import { ref, watchEffect } from "vue";

import Button from "primevue/button";
import Drawer from "primevue/drawer";
import Skeleton from "primevue/skeleton";
import ToggleSwitch from "primevue/toggleswitch";

import NotificationRow from "@/arches_lingo/components/header/PageHeader/components/NotificationsInteraction/components/NotificationRow.vue";

import {
    fetchUserNotifications,
    dismissNotifications,
} from "@/arches_lingo/api.ts";
import type { Notification } from "@/arches_lingo/types.ts";

const isLoading = ref(false);
const notifications = ref<Notification[]>([]);
const showUnreadOnly = ref(true);

const shouldShowNotificationsPanel = defineModel(
    "shouldShowNotificationsPanel",
    {
        type: Boolean,
        default: false,
    },
);

async function loadNotifications(unreadOnly: boolean) {
    isLoading.value = true;
    const parsed = await fetchUserNotifications(unreadOnly);
    notifications.value = parsed?.notifications;
    isLoading.value = false;
}

function dismissAllNotifications() {
    dismissNotifications(notifications.value.map((n) => n.id));
    notifications.value = [];
}

watchEffect(() => {
    if (shouldShowNotificationsPanel.value) {
        loadNotifications(false); // Load all notifications (even read ones)
    }
});
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
                    backgroundColor: 'var(--p-header-toolbar-background)',
                    borderBottom:
                        '0.0625rem solid var(--p-header-toolbar-border)',
                    padding: '0.25rem 0.75rem',
                    fontFamily: 'var(--p-lingo-font-family)',
                    fontSize: 'var(--p-lingo-font-size-medium)',
                },
            },
            footer: {
                style: {
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                    borderTop: '0.0625rem solid var(--p-header-toolbar-border)',
                    backgroundColor: 'var(--p-header-toolbar-background)',
                    padding: '0.5rem 0.75rem',
                    fontFamily: 'var(--p-lingo-font-family)',
                },
            },
        }"
    >
        <template #default>
            <Skeleton
                v-if="isLoading"
                style="width: 100%"
            />
            <span v-else>
                <div
                    v-if="
                        showUnreadOnly &&
                        notifications.filter((notif) => notif.isread === false)
                            .length === 0
                    "
                    class="notification-row"
                >
                    {{ $gettext("You do not have any notifications.") }}
                </div>
                <div
                    v-for="notification in notifications"
                    v-else
                    :key="notification.id"
                    class="notification-row"
                >
                    <NotificationRow
                        v-if="!showUnreadOnly || notification.isread === false"
                        :notification="notification"
                    />
                </div>
            </span>
        </template>

        <template #footer>
            <span style="display: flex; align-items: center; gap: 0.5rem">
                <ToggleSwitch
                    v-model="showUnreadOnly"
                    input-id="show-unread-only"
                    class="footer-btn"
                />
                <label for="show-unread-only">{{
                    $gettext("Show Unread Only")
                }}</label>
            </span>
            <Button
                :label="$gettext('Dismiss All')"
                :disabled="notifications.length === 0"
                severity="danger"
                class="footer-btn"
                @click="dismissAllNotifications"
            />
        </template>
    </Drawer>
</template>

<style scoped>
.notification-row {
    display: flex;
    justify-content: space-between;
    border-bottom: 0.0625rem solid var(--p-header-toolbar-border);
    padding: 1rem;
}
.footer-btn {
    font-family: var(--p-lingo-font-family);
}
</style>
