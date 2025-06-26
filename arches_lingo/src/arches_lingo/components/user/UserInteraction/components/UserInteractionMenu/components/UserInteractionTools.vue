<script setup lang="ts">
import { useRouter } from "vue-router";
import { useGettext } from "vue3-gettext";
import { useToast } from "primevue/usetoast";

import Button from "primevue/button";
import ConfirmDialog from "primevue/confirmdialog";

import { logout } from "@/arches_lingo/api.ts";
import { DEFAULT_ERROR_TOAST_LIFE, ERROR } from "@/arches_lingo/constants.ts";
import { routeNames } from "@/arches_lingo/routes.ts";

const toast = useToast();
const { $gettext } = useGettext();
const router = useRouter();

async function issueLogout() {
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
}
</script>

<template>
    <div>
        <div class="section-title">{{ $gettext("Tools") }}</div>

        <Button
            severity="secondary"
            :aria-label="$gettext('Logout')"
            @click="issueLogout"
        >
            <i
                class="pi pi-sign-out"
                aria-hidden="true"
            ></i>
            <span>{{ $gettext("Logout") }}</span>
        </Button>
    </div>
</template>

<style scoped>
.section-title {
    color: var(--p-text-muted-color);
    margin-bottom: 0.5rem;
}
</style>
