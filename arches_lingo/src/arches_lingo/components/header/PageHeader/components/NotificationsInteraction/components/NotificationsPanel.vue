<script setup lang="ts">
import { onMounted, ref, watch } from "vue";

import Button from "primevue/button";
import Drawer from "primevue/drawer";
import ProgressBar from "primevue/progressbar";
import ToggleSwitch from "primevue/toggleswitch";
import VirtualScroller, {
    type VirtualScrollerLazyEvent,
} from "primevue/virtualscroller";

import NotificationRow from "@/arches_lingo/components/header/PageHeader/components/NotificationsInteraction/components/NotificationRow.vue";

import {
    fetchUserNotifications,
    dismissNotifications,
} from "@/arches_lingo/api.ts";
import type { Notification, PaginatorDetails } from "@/arches_lingo/types.ts";

import {
    SEARCH_RESULTS_PER_PAGE,
    SEARCH_RESULT_ITEM_SIZE,
} from "@/arches_lingo/constants.ts";

const notifications = ref<Notification[]>([]);
const isLoading = ref(false);
const showUnreadOnly = ref(true);
const currentPageNumber = ref(1);
const paginator = ref<PaginatorDetails | null>(null);
const resultsPerPage = ref(SEARCH_RESULTS_PER_PAGE);

const shouldShowNotificationsPanel = defineModel(
    "shouldShowNotificationsPanel",
    {
        type: Boolean,
        default: false,
    },
);

async function loadNotifications(
    items: number,
    pageNumber: number,
    unreadOnly: boolean,
) {
    isLoading.value = true;
    const parsed = await fetchUserNotifications(items, pageNumber, unreadOnly);
    notifications.value = [
        ...notifications.value,
        ...(parsed?.notifications ?? []),
    ];
    paginator.value = parsed.paginator;
    isLoading.value = false;
}

function dismissAllNotifications() {
    dismissNotifications(
        notifications.value.map((notification) => notification.id),
    );
    notifications.value = [];
}

function loadAdditionalNotifications(event: VirtualScrollerLazyEvent) {
    if (
        paginator.value?.has_next &&
        paginator.value?.total_pages !== currentPageNumber.value &&
        event.last >= notifications.value.length - 1
    ) {
        loadNotifications(
            resultsPerPage.value,
            (currentPageNumber.value += 1),
            showUnreadOnly.value,
        );
    }
}

function resetNotifications() {
    notifications.value = [];
    currentPageNumber.value = 1;
}

watch(showUnreadOnly, () => {
    resetNotifications();
    loadNotifications(
        resultsPerPage.value,
        1, // start from beginning if we're changing the unread filter
        showUnreadOnly.value,
    );
});

onMounted(() => {
    resetNotifications();
    loadNotifications(resultsPerPage.value, 1, showUnreadOnly.value);
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
            <template v-if="notifications.length === 0 && !isLoading">
                <div class="notification-row">
                    <span>
                        {{
                            showUnreadOnly
                                ? $gettext("You have no new notifications")
                                : $gettext("You have no notifications")
                        }}
                    </span>
                </div>
            </template>
            <VirtualScroller
                :items="notifications"
                :item-size="SEARCH_RESULT_ITEM_SIZE"
                style="height: 100%"
                lazy
                :num-tolerated-items="1"
                @lazy-load="loadAdditionalNotifications"
            >
                <template #item="{ item: notification }">
                    <div class="notification-row">
                        <NotificationRow :notification="notification" />
                    </div>
                </template>
            </VirtualScroller>
            <ProgressBar
                v-if="isLoading"
                mode="indeterminate"
                style="height: 0.5rem"
            />
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
    align-items: center;
    justify-content: space-between;
    border-bottom: 0.0625rem solid var(--p-header-toolbar-border);
    padding: 1rem;
}
.footer-btn {
    font-family: var(--p-lingo-font-family);
}
:deep(.p-progressbar .p-progressbar-value) {
    background: var(--p-primary-800);
}
</style>
