<script setup lang="ts">
import { provide, ref, watchEffect } from "vue";
import { useRouter, useRoute } from "vue-router";
import { useGettext } from "vue3-gettext";
import { useToast } from "primevue/usetoast";

import Splitter from "primevue/splitter";
import SplitterPanel from "primevue/splitterpanel";
import Toast from "primevue/toast";

import SchemeHierarchy from "@/arches_lingo/components/header/PageHeader/components/SchemeHierarchy/SchemeHierarchy.vue";

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
import PageHeader from "@/arches_lingo/components/header/PageHeader/PageHeader.vue";
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

const isNavExpanded = ref(false);
const shouldShowHierarchy = ref(false);

const schemeHierarchyKey = ref(0);

const refreshSchemeHierarchy = function () {
    schemeHierarchyKey.value++;
};
provide("refreshSchemeHierarchy", refreshSchemeHierarchy);

watchEffect(() => {
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
});

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
            <Splitter style="height: 100%; min-height: 0; border: none">
                <SplitterPanel v-show="shouldShowHierarchy">
                    <div style="height: 100%; overflow: auto">
                        <SchemeHierarchy
                            :key="schemeHierarchyKey"
                            @should-show-hierarchy="
                                shouldShowHierarchy = $event
                            "
                        />
                    </div>
                </SplitterPanel>
                <SplitterPanel>
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
</template>

<style scoped>
@import url("https://fonts.googleapis.com/css2?family=Open+Sans:ital,wdth,wght@0,75..100,300..800;1,75..100,300..800&display=swap");
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

<!-- NOT scoped because dialog gets appended to <body> and is unreachable via scoped styles -->
<style>
@import url("https://fonts.googleapis.com/css2?family=Open+Sans:ital,wdth,wght@0,75..100,300..800;1,75..100,300..800&display=swap");
.p-confirmdialog,
.p-datepicker-panel,
.p-tree-node-label,
.p-toast,
.p-inputtext,
.p-treeselect-empty-message,
.p-treeselect-option,
.p-select-option,
.p-select-empty-message,
.p-multiselect-empty-message,
.p-multiselect-option {
    font-family: var(--p-lingo-font-family) !important;
}
</style>
