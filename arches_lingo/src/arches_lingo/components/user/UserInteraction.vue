<script setup lang="ts">
import { computed, inject } from "vue";
import { useRouter } from "vue-router";
import { useGettext } from "vue3-gettext";

import { useToast } from "primevue/usetoast";
import Button from "primevue/button";

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

const issueLogout = async () => {
    try {
        await logout();
        router.push({ name: routeNames.login });
    } catch (error) {
        toast.add({
            severity: ERROR,
            life: DEFAULT_ERROR_TOAST_LIFE,
            summary: $gettext("Sign out failed."),
            detail: error instanceof Error ? error.message : undefined,
        });
    }
};

const greeting = computed(() => {
    if (!user.value) {
        return "";
    }
    if (user.value.first_name && user.value.last_name) {
        return $gettext("Hello %{first} %{last}", {
            first: user.value.first_name,
            last: user.value.last_name,
        });
    } else {
        return $gettext("Hello %{username}", { username: user.value.username });
    }
});
</script>

<template>
    <div style="display: flex; align-items: center; gap: 1rem">
        <span v-if="user">{{ greeting }}</span>
        <Button
            :label="$gettext('Sign out')"
            @click="issueLogout"
        ></Button>
    </div>
</template>
