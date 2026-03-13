<script setup lang="ts">
import { onMounted, provide, ref, watchEffect } from "vue";
import { useRouter, useRoute } from "vue-router";
import { useGettext } from "vue3-gettext";
import { useToast } from "primevue/usetoast";

import Splitter from "primevue/splitter";
import SplitterPanel from "primevue/splitterpanel";
import ConfirmDialog from "primevue/confirmdialog";
import Toast from "primevue/toast";

import SchemeHierarchy from "@/arches_lingo/components/header/PageHeader/components/SchemeHierarchy/SchemeHierarchy.vue";

import { DEFAULT_ERROR_TOAST_LIFE, ERROR } from "@/arches_lingo/constants.ts";

import { routeNames } from "@/arches_lingo/routes.ts";
import { useUnsavedChangesGuard } from "@/arches_lingo/composables/useUnsavedChangesGuard.ts";
import { useAppSettingsStore } from "@/arches_lingo/stores/useAppSettingsStore.ts";
import { useLanguageStore } from "@/arches_lingo/stores/useLanguageStore.ts";
import { useUserStore } from "@/arches_lingo/stores/useUserStore.ts";
import PageHeader from "@/arches_lingo/components/header/PageHeader/PageHeader.vue";
import SideNav from "@/arches_lingo/components/sidenav/SideNav.vue";

import type { RouteLocationNormalizedLoadedGeneric } from "vue-router";

const { $gettext } = useGettext();
const appSettingsStore = useAppSettingsStore();
const languageStore = useLanguageStore();
const userStore = useUserStore();

const router = useRouter();
const route = useRoute();
const toast = useToast();

const isNavExpanded = ref(false);
const shouldShowHierarchy = ref(false);

const schemeHierarchyKey = ref(0);

const refreshSchemeHierarchy = function () {
    schemeHierarchyKey.value++;
};
provide("refreshSchemeHierarchy", refreshSchemeHierarchy);

onMounted(function () {
    useUnsavedChangesGuard(router);
    languageStore.initialize();
});

watchEffect(() => {
    router.beforeEach(async (to, _from, next) => {
        if (to.name === routeNames.login) {
            shouldShowHierarchy.value = false;
            next();
            return;
        }
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
});

async function checkUserAuthentication(
    to: RouteLocationNormalizedLoadedGeneric,
) {
    await Promise.all([userStore.initialize(), appSettingsStore.initialize()]);

    const requiresAuthentication = to.matched.some(
        (record) => record.meta.requiresAuthentication,
    );

    if (
        userStore.isAnonymous &&
        (!appSettingsStore.allowAnonymousAccess || requiresAuthentication)
    ) {
        throw new Error($gettext("Authentication required."));
    }
}
</script>

<template>
    <main>
        <SideNav
            v-if="route.meta.shouldShowNavigation"
            @update:is-nav-expanded="isNavExpanded = $event"
        />

        <div class="main-content">
            <PageHeader
                v-if="route.meta.shouldShowNavigation"
                v-model="shouldShowHierarchy"
                :is-nav-expanded="isNavExpanded"
            />
            <Splitter
                class="main-splitter"
                :pt="{
                    gutter: {
                        style: {
                            display: shouldShowHierarchy ? 'flex' : 'none',
                        },
                    },
                }"
            >
                <SplitterPanel
                    v-show="shouldShowHierarchy"
                    :size="25"
                >
                    <div class="hierarchy-panel">
                        <SchemeHierarchy
                            v-if="route.meta.shouldShowNavigation"
                            :key="schemeHierarchyKey"
                            :is-open="shouldShowHierarchy"
                            @should-show-hierarchy="
                                shouldShowHierarchy = $event
                            "
                        />
                    </div>
                </SplitterPanel>
                <SplitterPanel :size="75">
                    <RouterView :key="route.fullPath" />
                </SplitterPanel>
            </Splitter>
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
    <ConfirmDialog group="unsaved-changes" />
</template>

<style scoped>
main {
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

.main-splitter {
    height: 100%;
    border: none;
    overflow: hidden;
    border-radius: 0;
}

.hierarchy-panel {
    height: 100%;
    display: flex;
    flex-direction: column;
}
</style>

<style>
@import url("arches/arches/app/media/fonts/openSans.css");

:root {
    --p-font-family: var(--p-lingo-font-family);
}

html,
body {
    font-family: var(--p-lingo-font-family);
}

.p-component {
    font-family: var(--p-lingo-font-family);
}

.p-multiselect .button-container a {
    display: none;
}

.resource-instance-link {
    color: inherit;
    text-decoration: none;
    pointer-events: none;
}
</style>
