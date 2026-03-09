<script setup lang="ts">
import { computed, useTemplateRef } from "vue";
import { storeToRefs } from "pinia";
import { useGettext } from "vue3-gettext";
import { useRouter } from "vue-router";

import Button from "primevue/button";
import Popover from "primevue/popover";

import UserInteractionMenu from "@/arches_lingo/components/header/PageHeader/components/UserInteraction/components/UserInteractionMenu/UserInteractionMenu.vue";

import { useUserStore } from "@/arches_lingo/stores/useUserStore.ts";
import { routeNames } from "@/arches_lingo/routes.ts";

import type { PopoverMethods } from "primevue/popover";

const { $gettext } = useGettext();
const router = useRouter();
const userStore = useUserStore();
const { user } = storeToRefs(userStore);
const { isAnonymous } = userStore;

const popover = useTemplateRef<PopoverMethods>("popover");

const displayName = computed(() => {
    if (!user.value) return "";

    if (user.value.first_name && user.value.last_name) {
        // Using gettext here to handle localization-dependant
        // ordering of first name / last name
        return $gettext("%{firstName} %{lastName}", {
            firstName: user.value.first_name,
            lastName: user.value.last_name,
        });
    }

    return user.value.username;
});

const initials = computed(() => {
    if (!user.value) return "";

    const firstInitial = user.value.first_name?.charAt(0).toUpperCase();
    const lastInitial = user.value.last_name?.charAt(0).toUpperCase();

    if (firstInitial && lastInitial) {
        return `${firstInitial}${lastInitial}`;
    }

    return user.value.username.charAt(0).toUpperCase();
});

function openUserMenu(event: MouseEvent) {
    popover.value!.toggle(event);
}

function navigateToLogin() {
    router.push({ name: routeNames.login });
}
</script>

<template>
    <div class="user-interaction">
        <template v-if="isAnonymous">
            <Button
                :label="$gettext('Login')"
                :aria-label="$gettext('Login')"
                icon="pi pi-sign-in"
                @click="navigateToLogin"
            />
        </template>
        <template v-else>
            <Button
                :aria-label="$gettext('Open user menu')"
                @click="openUserMenu"
            >
                <div
                    v-if="initials"
                    class="initials-circle"
                >
                    {{ initials }}
                </div>
                <span>{{ displayName }}</span>
            </Button>

            <Popover
                ref="popover"
                class="user-interaction-popover"
            >
                <UserInteractionMenu
                    :display-name="displayName"
                    :email="user?.email ?? ''"
                />
            </Popover>
        </template>
    </div>
</template>

<style scoped>
.user-interaction {
    display: flex;
    align-items: center;
    gap: 0.5rem;
}

.user-interaction-popover {
    padding: 0.5rem;
}

.p-button {
    background: transparent !important;
    border: none !important;
    border-radius: 0 !important;
    color: inherit !important;
    font-size: 0.875rem;
}

.p-button:hover {
    background: var(
        --p-button-text-hover-background,
        var(--p-button-primary-hover-background)
    ) !important;
}

.initials-circle {
    width: 2rem;
    height: 2rem;
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    background-color: var(--p-primary-700);
    border: 0.09rem solid var(--p-primary-950);
}
</style>
