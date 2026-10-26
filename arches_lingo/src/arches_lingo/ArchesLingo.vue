<script setup lang="ts">
import { onMounted, provide, ref, watch, watchEffect } from "vue";
import { useRouter, useRoute } from "vue-router";
import { useGettext } from "vue3-gettext";
import type { RouteLocationNormalized } from "vue-router";

import Splitter from "primevue/splitter";
import SplitterPanel from "primevue/splitterpanel";
import ConfirmDialog from "primevue/confirmdialog";
import Toast from "primevue/toast";

import SchemeHierarchy from "@/arches_lingo/components/header/PageHeader/components/SchemeHierarchy/SchemeHierarchy.vue";

import { MAIN_CONTENT_ID } from "@/arches_lingo/constants.ts";
import { useUnsavedChangesGuard } from "@/arches_lingo/composables/useUnsavedChangesGuard.ts";
import { useConceptStore } from "@/arches_lingo/stores/useConceptStore.ts";
import { useLanguageStore } from "@/arches_lingo/stores/useLanguageStore.ts";
import PageHeader from "@/arches_lingo/components/header/PageHeader/PageHeader.vue";
import SideNav from "@/arches_lingo/components/sidenav/SideNav.vue";

const PRESERVED_QUERY_PARAMS = ["filter", "sort", "hierarchy", "lifecycle"];

const conceptStore = useConceptStore();
const languageStore = useLanguageStore();

const router = useRouter();
const route = useRoute();
const { $gettext } = useGettext();

const isNavExpanded = ref(false);
const schemeHierarchyKey = ref(0);
const shouldShowHierarchy = ref(
    Boolean(route.meta.shouldShowNavigation) && route.query.hierarchy === "1",
);

provide("refreshSchemeHierarchy", refreshSchemeHierarchy);

watchEffect(() => {
    document.documentElement.lang = languageStore.selectedLanguage.code;
    document.documentElement.dir =
        languageStore.selectedLanguage.default_direction ?? "ltr";
    document.body.dir = document.documentElement.dir;
});

onMounted(function () {
    languageStore.initialize();
    useUnsavedChangesGuard(router);

    router.beforeEach((to, from, next) => {
        const carriedQuery = getCarriedQuery(to, from);
        if (carriedQuery) {
            return next({ ...to, query: carriedQuery });
        }
        next();
    });
});

watch(shouldShowHierarchy, (isOpen) => {
    if (isOpen) {
        router.replace({ query: { ...route.query, hierarchy: "1" } });
        return;
    }
    const queryWithoutHierarchyParams = Object.fromEntries(
        Object.entries(route.query).filter(
            ([key]) => !PRESERVED_QUERY_PARAMS.includes(key),
        ),
    );
    router.replace({ query: queryWithoutHierarchyParams });
});

watch(
    () => route.name,
    () => {
        if (!route.meta.shouldShowNavigation) {
            shouldShowHierarchy.value = false;
        }
    },
);

watch(
    () => route.params.id,
    (newId, oldId) => {
        if (oldId === "new" && newId && newId !== "new") {
            refreshSchemeHierarchy();
        }
    },
);

function getCarriedQuery(
    to: RouteLocationNormalized,
    from: RouteLocationNormalized,
) {
    if (to.path === from.path) return null;

    const missingParams = PRESERVED_QUERY_PARAMS.filter(
        (param) =>
            from.query[param] !== undefined && to.query[param] === undefined,
    );

    if (!missingParams.length) {
        return null;
    }

    return {
        ...to.query,
        ...Object.fromEntries(
            missingParams.map((param) => [param, from.query[param]]),
        ),
    };
}

function refreshSchemeHierarchy() {
    conceptStore.refresh();
    schemeHierarchyKey.value++;
}
</script>

<template>
    <div class="app-shell">
        <SideNav
            v-if="route.meta.shouldShowNavigation"
            @update:is-nav-expanded="isNavExpanded = $event"
        />

        <div class="app-content">
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
                    <aside
                        class="hierarchy-panel"
                        :aria-label="$gettext('Explore')"
                    >
                        <SchemeHierarchy
                            v-if="route.meta.shouldShowNavigation"
                            :key="schemeHierarchyKey"
                            :is-open="shouldShowHierarchy"
                            @should-show-hierarchy="
                                shouldShowHierarchy = $event
                            "
                        />
                    </aside>
                </SplitterPanel>
                <SplitterPanel :size="75">
                    <main
                        :id="MAIN_CONTENT_ID"
                        class="page-content"
                    >
                        <RouterView :key="route.path" />
                    </main>
                </SplitterPanel>
            </Splitter>
        </div>
    </div>
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
    <ConfirmDialog group="logout" />
</template>

<style scoped>
.app-shell {
    height: 100vh;
    width: 100vw;
    overflow: hidden;
    display: flex;
}

.app-content {
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

.page-content {
    height: 100%;
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
