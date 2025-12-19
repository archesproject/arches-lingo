<script setup lang="ts">
import { onMounted, ref, watch } from "vue";
import { useGettext } from "vue3-gettext";

import Button from "primevue/button";
import type { VirtualScrollerLazyEvent } from "primevue/virtualscroller";

import NotificationsPanel from "@/arches_lingo/components/header/PageHeader/components/NotificationsInteraction/components/NotificationsPanel.vue";
import { fetchUserNotifications } from "@/arches_lingo/api.ts";
import type { Notification, PaginatorDetails } from "@/arches_lingo/types.ts";
import { SEARCH_RESULTS_PER_PAGE } from "@/arches_lingo/constants.ts";

const { $gettext } = useGettext();

const shouldShowNotificationsPanel = ref(false);
const notifications = ref<Notification[]>([]);
const isLoading = ref(false);
const showUnreadOnly = ref(true);
const currentPageNumber = ref(1);
const paginator = ref<PaginatorDetails | null>(null);
const resultsPerPage = ref(SEARCH_RESULTS_PER_PAGE);

function activateHierarchyOverlay() {
    shouldShowNotificationsPanel.value = true;
}

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
    paginator.value = null;
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
            v-model:notifications="notifications"
            v-model:is-loading="isLoading"
            v-model:show-unread-only="showUnreadOnly"
            @load-additional-notifications="loadAdditionalNotifications"
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
