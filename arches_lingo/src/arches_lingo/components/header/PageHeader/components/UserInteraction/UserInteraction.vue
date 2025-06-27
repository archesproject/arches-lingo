<script setup lang="ts">
import { computed, inject, useTemplateRef } from "vue";
import { useGettext } from "vue3-gettext";

import Button from "primevue/button";
import Popover from "primevue/popover";

import UserInteractionMenu from "@/arches_lingo/components/header/PageHeader/components/UserInteraction/components/UserInteractionMenu/UserInteractionMenu.vue";

import { USER_KEY } from "@/arches_lingo/constants.ts";

import type { PopoverMethods } from "primevue/popover";
import type { UserRefAndSetter } from "@/arches_lingo/types.ts";

const { $gettext } = useGettext();
const { user } = inject(USER_KEY) as UserRefAndSetter;

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
            <span>{{ displayName }}</span>
        </Button>

        <Popover
            ref="popover"
            style="padding: 1rem 0.5rem"
        >
            <UserInteractionMenu
                :display-name="displayName"
                :email="user!.email"
            />
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
    background-color: var(--p-primary-700);
    border: 0.09rem solid var(--p-primary-950);
}
</style>
