<script setup lang="ts">
import { computed } from "vue";
import { useGettext } from "vue3-gettext";

import { useToast } from "primevue/usetoast";
import Button from "primevue/button";

import { DEFAULT_ERROR_TOAST_LIFE, ERROR } from "@/arches_lingo/constants.ts";
import { logout } from "@/arches_lingo/api.ts";

import type { User } from "@/arches_lingo/types";

const user = defineModel<User | null>({ required: true });

const { $gettext } = useGettext();
const toast = useToast();

const issueLogout = async () => {
    try {
        await logout();
        user.value = null;
    } catch (error) {
        toast.add({
            severity: ERROR,
            life: DEFAULT_ERROR_TOAST_LIFE,
            summary: $gettext("Sign out failed."),
            detail: error instanceof Error ? error.message : undefined,
        });
    }
};

const bestName = computed(() => {
    if (!user.value) {
        return "";
    }
    // TODO: determine appropriate i18n for this.
    if (user.value.first_name && user.value.last_name) {
        return user.value.first_name + " " + user.value.last_name;
    }
    return user.value.username;
});
</script>

<template>
    <main>
        <div style="display: flex; justify-content: space-between">
            <h1>{{ $gettext("LINGO") }}</h1>
            <span>{{ $gettext("Hello %{bestName}", { bestName }) }}</span>
            <Button @click="issueLogout">
                {{ $gettext("Sign out") }}
            </Button>
        </div>
    </main>
</template>
