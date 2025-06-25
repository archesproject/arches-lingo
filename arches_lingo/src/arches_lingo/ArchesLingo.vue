<script setup lang="ts">
import { provide, ref } from "vue";
import { useRouter, useRoute } from "vue-router";
import { useGettext } from "vue3-gettext";

import Toast from "primevue/toast";
import { useToast } from "primevue/usetoast";

import {
    ANONYMOUS,
    DEFAULT_ERROR_TOAST_LIFE,
    ENGLISH,
    ERROR,
    USER_KEY,
    selectedLanguageKey,
    systemLanguageKey,
} from "@/arches_lingo/constants.ts";

import { routeNames } from "@/arches_lingo/routes.ts";
import { fetchUser } from "@/arches_lingo/api.ts";
import PageHeader from "@/arches_lingo/components/header/PageHeader.vue";
import SideNav from "@/arches_lingo/components/sidenav/SideNav.vue";

import type { Ref } from "vue";
import type { Language } from "@/arches_component_lab/types";
import type { User } from "@/arches_lingo/types";
import type { RouteLocationNormalizedLoadedGeneric } from "vue-router";

const user = ref<User | null>(null);
const setUser = (userToSet: User | null) => {
    user.value = userToSet;
};
provide(USER_KEY, { user, setUser });

const selectedLanguage: Ref<Language> = ref(ENGLISH);
provide(selectedLanguageKey, selectedLanguage);
const systemLanguage = ENGLISH; // TODO: get from settings
provide(systemLanguageKey, systemLanguage);

const router = useRouter();
const route = useRoute();
const toast = useToast();
const { $gettext } = useGettext();

async function checkUserAuthentication(
    to: RouteLocationNormalizedLoadedGeneric,
) {
    const userData = await fetchUser();
    setUser(userData);

    const requiresAuthentication = to.matched.some(
        (record) => record.meta.requiresAuthentication,
    );
    if (requiresAuthentication && userData.username === ANONYMOUS) {
        throw new Error($gettext("Authentication required."));
    }
}

router.beforeEach(async (to, _from, next) => {
    try {
        await checkUserAuthentication(to);

        next();
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
        <SideNav v-if="route.meta.shouldShowNavigation" />

        <div class="main-content">
            <PageHeader v-if="route.meta.shouldShowNavigation" />
            <RouterView :key="route.fullPath" />
        </div>
    </main>
    <Toast
        :pt="{
            summary: { fontSize: 'medium' },
            detail: { fontSize: 'small' },
            messageIcon: {
                style: { marginTop: 'var(--p-toast-messageicon-margintop)' },
            },
        }"
    />
</template>

<style scoped>
main {
    font-family: var(--p-lingo-font-family);
    height: 100vh;
    width: 100vw;
    overflow: hidden;
    display: flex;
}

.main-content {
    display: flex;
    flex-direction: column;
    flex: 1 1 auto;
    overflow: hidden;
}
</style>
