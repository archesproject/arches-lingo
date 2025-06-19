<script setup lang="ts">
import { computed, inject, useTemplateRef } from "vue";
import { useRouter } from "vue-router";
import { useGettext } from "vue3-gettext";
import { useToast } from "primevue/usetoast";

import Button from "primevue/button";
import Popover, { type PopoverMethods } from "primevue/popover";

import UserInteractionMenu from "@/arches_lingo/components/user/UserInteraction/components/UserInteractionMenu.vue";

import { logout } from "@/arches_lingo/api.ts";
import {
    DEFAULT_ERROR_TOAST_LIFE,
    ERROR,
    USER_KEY,
} from "@/arches_lingo/constants.ts";
import { routeNames } from "@/arches_lingo/routes.ts";

import type { UserRefAndSetter } from "@/arches_lingo/types.ts";

const { $gettext } = useGettext();
const toast = useToast();
const router = useRouter();
const { user } = inject(USER_KEY) as UserRefAndSetter;

const popover = useTemplateRef<PopoverMethods>("popover");

const greeting = computed(() => {
    if (!user.value) return "";

    if (user.value.first_name && user.value.last_name) {
        return $gettext("%{first} %{last}", {
            first: user.value.first_name,
            last: user.value.last_name,
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

// async function issueLogout() {
//     try {
//         await logout();
//         router.push({ name: routeNames.login });
//     } catch (error) {
//         toast.add({
//             severity: ERROR,
//             life: DEFAULT_ERROR_TOAST_LIFE,
//             summary: $gettext("Sign out failed."),
//             detail: error instanceof Error ? error.message : undefined,
//         });
//     }
// }

function openUserMenu(event: MouseEvent) {
    popover!.value!.toggle(event);
}
</script>

<template>
    <div style="display: flex; align-items: center; gap: 0.5rem">
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
            <span v-if="user">{{ greeting }}</span>
        </Button>

        <Popover ref="popover">
            <UserInteractionMenu :user="user" />
        </Popover>
    </div>
</template>

<style scoped>
.p-button {
    background: var(--p-menubar-background) !important;
    border: none !important;
    color: var(--p-menubar-text-color) !important;
}

.p-button:hover {
    background: var(--p-button-primary-hover-background) !important;
}
.initials-circle {
    width: 2rem;
    height: 2rem;
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    font-weight: var(--p-lingo-font-weight-bold);
    background-color: var(--p-primary-700);
    border: 0.09rem solid var(--p-primary-950);
    user-select: none;
}
</style>
