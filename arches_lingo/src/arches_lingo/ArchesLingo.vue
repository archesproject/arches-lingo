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
import HierarchySplitter from "@/arches_lingo/components/tree/HierarchySplitter.vue";
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

function carryOverShowHierarchy(to: RouteLocationNormalizedLoadedGeneric) {
    const currentUrl = new URL(window.location.href);
    const currentShowHierarchy = currentUrl.searchParams.get("showHierarchy");

    if (
        currentShowHierarchy &&
        to.matched.some((record) => record.meta.shouldShowHierarchy) &&
        !to.query.showHierarchy
    ) {
        return {
            name: to.name,
            params: to.params,
            query: {
                ...to.query,
                showHierarchy: currentShowHierarchy,
            },
        };
    }
    return null;
}

router.beforeEach(async (to, _from, next) => {
    try {
        await checkUserAuthentication(to);
        const newLocation = carryOverShowHierarchy(to);

        if (newLocation) {
            return next(newLocation);
        }

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
        <div class="nav-container">
            <SideNav v-if="route.meta.shouldShowNavigation" />
            <div class="main-content">
                <PageHeader v-if="route.meta.shouldShowNavigation" />
                <div class="content-panel">
                    <HierarchySplitter v-if="route.meta.shouldShowHierarchy" />
                    <RouterView v-else />
                </div>
            </div>
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
    flex-direction: column;
}

.nav-container {
    display: flex;
    flex-direction: row;
    flex: 1 1 100vh;
}

.main-content {
    display: flex;
    flex-direction: column;
    flex: 1 1 auto;
    overflow: hidden;
}

.content-panel {
    display: flex;
    flex-direction: column;
    flex: 1 1 auto;
    min-width: 0;
}
</style>
