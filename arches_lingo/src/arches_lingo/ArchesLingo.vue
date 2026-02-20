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

// Return the native/autonym name for a language code using the
// browser's Intl API (e.g. "de" → "Deutsch", "en" → "English").
function getAutonym(code: string, fallback: string): string {
    try {
        const name = new Intl.DisplayNames([code], { type: "language" }).of(
            code,
        );
        if (name) {
            return name.charAt(0).toUpperCase() + name.slice(1);
        }
    } catch {
        // Intl.DisplayNames may not support every code.
    }
    return fallback;
}

// Build initial available languages from gettext.available (populated from
// settings.LANGUAGES via the i18n endpoint in create-vue-application).
// These use placeholder values for DB-specific fields until the real
// Language records are fetched from the database.
const enabledCodes = new Set(Object.keys(gettext.available));
const enabledLanguages: Language[] = Object.entries(gettext.available).map(
    ([code, name], index) => ({
        code,
        name: getAutonym(code, name),
        default_direction: "ltr" as const,
        id: index,
        isdefault: false,
        scope: "system",
    }),
);

// System language: gettext.current is initialised from get_language(),
// which defaults to LANGUAGE_CODE when no cookie is set.
const systemLanguageCode: string = gettext.current ?? "en";
const systemLang =
    enabledLanguages.find((l: Language) => l.code === systemLanguageCode) ??
    enabledLanguages[0];
const systemLanguage: Language = reactive(
    systemLang
        ? { ...systemLang, isdefault: true }
        : {
              code: systemLanguageCode,
              default_direction: "ltr" as const,
              id: 0,
              isdefault: true,
              name: systemLanguageCode,
              scope: "system",
          },
);

// Match browser locale to the best available language.
function matchBrowserLocale(languages: Language[]): Language | undefined {
    if (!languages.length) return undefined;
    const browserLangs = navigator.languages ?? [navigator.language];
    for (const browserTag of browserLangs) {
        const normalized = browserTag.toLowerCase();
        // Exact match (e.g. "en-gb" === "en-gb")
        const exact = languages.find((l) => l.code === normalized);
        if (exact) return exact;
        // Primary subtag match (e.g. "en-US" → "en")
        const primary = normalized.split("-")[0];
        const partial = languages.find((l) => l.code === primary);
        if (partial) return partial;
        // Match language whose code starts with the primary subtag
        const prefix = languages.find((l) => l.code.startsWith(primary));
        if (prefix) return prefix;
    }
    return undefined;
}

// Determine initial language priority:
// 1. django_language cookie (user's previous explicit choice)
// 2. Browser locale best-match
// 3. System language (LANGUAGE_CODE)
// 4. First enabled language
const cookieLanguageCode = Cookies.get("django_language");
const cookieMatch = cookieLanguageCode
    ? enabledLanguages.find((l) => l.code === cookieLanguageCode)
    : undefined;
const browserMatch = matchBrowserLocale(enabledLanguages);
const initialLanguage =
    cookieMatch ?? browserMatch ?? systemLang ?? enabledLanguages[0];

const availableLanguages: Ref<Language[]> = ref(enabledLanguages);
const selectedLanguage: Ref<Language> = ref(
    initialLanguage ?? { ...systemLanguage },
);

provide(availableLanguagesKey, availableLanguages);
provide(selectedLanguageKey, selectedLanguage);
provide(systemLanguageKey, systemLanguage);

// Sync gettext current language with initial selection.
if (initialLanguage && gettext.current !== initialLanguage.code) {
    gettext.current = initialLanguage.code;
}

// Fetch full Language records from the database and replace the
// placeholder objects with real DB values (default_direction, id, etc.).
onMounted(async () => {
    try {
        const dbLanguages = await fetchLanguages();
        const dbByCode = new Map(dbLanguages.map((l) => [l.code, l]));
        // Keep only languages that are both in the DB and in
        // settings.LANGUAGES (enabledCodes from gettext.available).
        const merged: Language[] = [];
        for (const code of enabledCodes) {
            const dbLang = dbByCode.get(code);
            if (dbLang) {
                // Use the autonym so the selector always shows the
                // language name in its own locale.
                merged.push({
                    ...dbLang,
                    name: getAutonym(dbLang.code, dbLang.name),
                });
            } else {
                // Language is in settings.LANGUAGES but not in DB —
                // keep the placeholder (already has autonym).
                const placeholder = enabledLanguages.find(
                    (l) => l.code === code,
                );
                if (placeholder) merged.push(placeholder);
            }
        }
        availableLanguages.value = merged;

        // Update selectedLanguage and systemLanguage with DB values.
        const dbSelected = dbByCode.get(selectedLanguage.value.code);
        if (dbSelected) {
            selectedLanguage.value = {
                ...dbSelected,
                name: getAutonym(dbSelected.code, dbSelected.name),
            };
        }
        const dbSystem = dbByCode.get(systemLanguage.code);
        if (dbSystem) {
            Object.assign(systemLanguage, {
                ...dbSystem,
                name: getAutonym(dbSystem.code, dbSystem.name),
            });
        }
    } catch {
        // If the fetch fails, keep the placeholder Language objects.
    }
});

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
