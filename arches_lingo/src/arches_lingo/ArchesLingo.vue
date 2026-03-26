<script setup lang="ts">
import { onMounted, provide, ref, watch } from "vue";
import { useRouter, useRoute } from "vue-router";
import type { RouteLocationNormalized } from "vue-router";

import Splitter from "primevue/splitter";
import SplitterPanel from "primevue/splitterpanel";
import ConfirmDialog from "primevue/confirmdialog";
import Toast from "primevue/toast";

import SchemeHierarchy from "@/arches_lingo/components/header/PageHeader/components/SchemeHierarchy/SchemeHierarchy.vue";

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

const isNavExpanded = ref(false);
const schemeHierarchyKey = ref(0);
const shouldShowHierarchy = ref(
    Boolean(route.meta.shouldShowNavigation) && route.query.hierarchy === "1",
);

provide("refreshSchemeHierarchy", refreshSchemeHierarchy);

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
                    <RouterView :key="route.path" />
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
