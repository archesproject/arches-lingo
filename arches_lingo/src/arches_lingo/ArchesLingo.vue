<script setup lang="ts">
import Cookies from "js-cookie";

import { onMounted, provide, reactive, ref, watch, watchEffect } from "vue";
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
    DEFAULT_LANGUAGE,
    ERROR,
    USER_KEY,
    availableLanguagesKey,
    selectedLanguageKey,
    systemLanguageKey,
} from "@/arches_lingo/constants.ts";

import { routeNames } from "@/arches_lingo/routes.ts";
import {
    fetchI18nData,
    fetchLanguages,
    fetchUser,
} from "@/arches_lingo/api.ts";
import PageHeader from "@/arches_lingo/components/header/PageHeader/PageHeader.vue";
import SideNav from "@/arches_lingo/components/sidenav/SideNav.vue";
import { getAutonym, matchBrowserLocale } from "@/arches_lingo/utils.ts";

import type { Ref } from "vue";
import type { Language } from "@/arches_component_lab/types";
import type { User } from "@/arches_lingo/types";
import type { RouteLocationNormalizedLoadedGeneric } from "vue-router";

const user = ref<User | null>(null);
const setUser = (userToSet: User | null) => {
    user.value = userToSet;
};
provide(USER_KEY, { user, setUser });

const gettext = useGettext();
const { $gettext } = gettext;

// Language state — populated from the backend in onMounted.
// System language is initialised from get_language() (Django's LANGUAGE_CODE).
// enabledCodes comes from settings.LANGUAGES via the i18n endpoint.
const enabledCodes = new Set(Object.keys(gettext.available));
const systemLanguageCode: string = gettext.current ?? DEFAULT_LANGUAGE.code;
const availableLanguages: Ref<Language[]> = ref([]);
const selectedLanguage: Ref<Language> = ref({
    ...DEFAULT_LANGUAGE,
    code: systemLanguageCode,
    name: systemLanguageCode,
});
const systemLanguage: Language = reactive({
    ...DEFAULT_LANGUAGE,
    code: systemLanguageCode,
    name: systemLanguageCode,
    isdefault: true,
});

provide(availableLanguagesKey, availableLanguages);
provide(selectedLanguageKey, selectedLanguage);
provide(systemLanguageKey, systemLanguage);

// When the selected language changes, update gettext and reload translations.
watch(
    () => selectedLanguage.value,
    async (newLang, oldLang) => {
        if (newLang.code === oldLang?.code) return;

        // Set the django_language cookie so subsequent requests use the new language.
        Cookies.set("django_language", newLang.code, {
            path: "/",
            sameSite: "Strict",
        });

        // Fetch translations for the new language.
        try {
            const i18nData = await fetchI18nData(newLang.code);
            // Merge new translations into the gettext translations object.
            Object.assign(gettext.translations, i18nData.translations);
            gettext.current = newLang.code;
        } catch {
            // Fall back to just switching the language code.
            gettext.current = newLang.code;
        }
    },
);

onMounted(async () => {
    try {
        const dbLanguages = await fetchLanguages();

        availableLanguages.value = dbLanguages
            .filter((lang) => enabledCodes.has(lang.code))
            .map((lang) => ({
                ...lang,
                name: getAutonym(lang.code, lang.name),
            }));

        const dbSystem =
            dbLanguages.find((lang) => lang.code === systemLanguageCode) ??
            dbLanguages.find((lang) => lang.isdefault);
        if (dbSystem) {
            Object.assign(systemLanguage, {
                ...dbSystem,
                name: getAutonym(dbSystem.code, dbSystem.name),
            });
        }

        // Determine initial language priority:
        // 1. django_language cookie (user's previous explicit choice)
        // 2. Browser locale best-match
        // 3. System language (LANGUAGE_CODE), if it is an enabled language
        // 4. First available language
        const cookieCode = Cookies.get("django_language");
        const cookieMatch = cookieCode
            ? availableLanguages.value.find((lang) => lang.code === cookieCode)
            : undefined;
        const browserMatch = matchBrowserLocale(availableLanguages.value);
        const systemMatch = availableLanguages.value.find(
            (lang) => lang.code === systemLanguageCode,
        );
        const initial =
            cookieMatch ??
            browserMatch ??
            systemMatch ??
            availableLanguages.value[0];

        if (initial) {
            selectedLanguage.value = initial;
            if (gettext.current !== initial.code) {
                gettext.current = initial.code;
            }
        }
    } catch {
        // If the fetch fails, keep the placeholder Language objects.
    }
});

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
</style>
