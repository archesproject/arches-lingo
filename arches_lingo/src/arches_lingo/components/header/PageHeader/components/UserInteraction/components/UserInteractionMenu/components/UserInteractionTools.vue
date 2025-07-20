<script setup lang="ts">
import { useRouter } from "vue-router";
import { useGettext } from "vue3-gettext";
import { useToast } from "primevue/usetoast";
import { useConfirm } from "primevue/useconfirm";

import Button from "primevue/button";
import ConfirmDialog from "primevue/confirmdialog";

import { generateArchesURL } from "@/arches/utils/generate-arches-url.ts";

import { logout } from "@/arches_lingo/api.ts";
import { DEFAULT_ERROR_TOAST_LIFE, ERROR } from "@/arches_lingo/constants.ts";
import { routeNames } from "@/arches_lingo/routes.ts";

const confirm = useConfirm();
const toast = useToast();
const { $gettext } = useGettext();
const router = useRouter();

function confirmLogout() {
    confirm.require({
        header: $gettext("Confirmation"),
        message: $gettext("Are you sure you want to log out?"),
        accept: () => {
            issueLogout();
        },
        rejectProps: {
            label: $gettext("Cancel"),
            outlined: true,
        },
        acceptProps: {
            label: $gettext("Logout"),
        },
    });
}

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

        <ConfirmDialog @click.stop.prevent />
        <div class="button-container">
            <Button
                as="a"
                :aria-label="$gettext('Logout')"
                @click="confirmLogout"
            >
                <i
                    class="pi pi-sign-out"
                    aria-hidden="true"
                ></i>
                <span>{{ $gettext("Logout") }}</span>
            </Button>

            <Button
                as="a"
                class="action-button"
                style="text-decoration: none"
                :href="generateArchesURL('user_profile_manager')"
                :aria-label="$gettext('My Profile')"
            >
                <i
                    class="pi pi-user"
                    aria-hidden="true"
                ></i>
                <span>{{ $gettext("My Profile") }}</span>
            </Button>
        </div>
    </div>
</template>

<style scoped>
.button-container {
    display: flex;
    gap: .15rem;
}

.p-button {
    font-size: var(--p-lingo-font-size-xsmall);
    margin-bottom: .15rem;
    width: 8rem;
    border: 0.0625rem solid var(--p-header-button-border);
}

.section-title {
    color: var(--p-text-muted-color);
    margin-bottom: 0.5rem;
}
</style>
