<script setup lang="ts">
import { provide, ref } from "vue";
import { useRouter, useRoute } from "vue-router";
import { useGettext } from "vue3-gettext";

import Toast from "primevue/toast";
import { useToast } from "primevue/usetoast";

import {
    ANONYMOUS,
    DEFAULT_ERROR_TOAST_LIFE,
    ERROR,
    USER_KEY,
} from "@/arches_lingo/constants.ts";

import { routeNames } from "@/arches_lingo/routes.ts";
import { fetchUser } from "@/arches_lingo/api.ts";

import type { User } from "@/arches_lingo/types.ts";

import PageHeader from "@/arches_lingo/components/header/PageHeader.vue";
import SideNav from "@/arches_lingo/components/sidenav/SideNav.vue";

const user = ref<User | null>(null);
const setUser = (userToSet: User | null) => {
    user.value = userToSet;
};
provide(USER_KEY, { user, setUser });

const router = useRouter();
const route = useRoute();
const toast = useToast();
const { $gettext } = useGettext();

router.beforeEach(async (to, _from, next) => {
    try {
        let userData = await fetchUser();
        setUser(userData);

        const requiresAuthentication = to.matched.some(
            (record) => record.meta.requiresAuthentication,
        );
        if (requiresAuthentication && userData.username === ANONYMOUS) {
            throw new Error();
        } else {
            next();
        }
    } catch (error) {
        if (to.name !== routeNames.root) {
            toast.add({
                severity: ERROR,
                life: DEFAULT_ERROR_TOAST_LIFE,
                summary: $gettext("Login required."),
                detail: error instanceof Error ? error.message : undefined,
            });
        }
        next({ name: routeNames.login });
    }
});
</script>

<template>
    <main>
        <PageHeader v-if="route.meta.shouldShowNavigation" />
        <div style="display: flex; flex: auto; flex-direction: row">
            <SideNav v-if="route.meta.shouldShowNavigation" />
            <div style="margin: 1rem; flex: auto">
                <RouterView />
            </div>
        </div>
    </main>
    <Toast />
</template>

<style scoped>
main {
    font-family: sans-serif;
    height: 100vh;
    width: 100vw;
    overflow-x: hidden;
    display: flex;
    flex-direction: column;
}
</style>
