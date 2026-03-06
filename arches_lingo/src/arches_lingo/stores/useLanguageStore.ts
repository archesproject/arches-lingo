import Cookies from "js-cookie";
import { ref } from "vue";
import { defineStore } from "pinia";
import { useGettext } from "vue3-gettext";

import { fetchI18nData, fetchLanguages } from "@/arches_lingo/api.ts";
import { FALLBACK_LANGUAGE } from "@/arches_lingo/constants.ts";
import { getAutonym } from "@/arches_lingo/utils.ts";

import type { Language } from "@/arches_component_lab/types";

export const useLanguageStore = defineStore("language", () => {
    const gettext = useGettext();

    const systemLanguageCode = gettext.current ?? FALLBACK_LANGUAGE.code;

    const selectedLanguage = ref<Language>({
        ...FALLBACK_LANGUAGE,
        code: systemLanguageCode,
        name: systemLanguageCode,
    });
    const systemLanguage = ref<Language>({
        ...FALLBACK_LANGUAGE,
        code: systemLanguageCode,
        name: systemLanguageCode,
        isdefault: true,
    });
    const availableLanguages = ref<Language[]>([]);

    async function setSelectedLanguage(lang: Language) {
        if (lang.code === selectedLanguage.value.code) return;
        selectedLanguage.value = lang;

        Cookies.set("django_language", lang.code, {
            path: "/",
            sameSite: "Strict",
        });

        try {
            const i18nData = await fetchI18nData(lang.code);
            Object.assign(gettext.translations, i18nData.translations);
            gettext.current = lang.code;
        } catch {
            gettext.current = lang.code;
        }
    }

    async function initialize() {
        try {
            const [dbLanguages, i18nData] = await Promise.all([
                fetchLanguages(),
                fetchI18nData(),
            ]);

            Object.assign(gettext.translations, i18nData.translations);

            const dbByCode = new Map(
                dbLanguages.map((lang) => [lang.code, lang]),
            );
            availableLanguages.value = Object.entries(
                i18nData.enabled_languages,
            ).map(([code, settingsName]) => {
                const dbLang = dbByCode.get(code);
                return dbLang
                    ? { ...dbLang, name: getAutonym(code, dbLang.name) }
                    : {
                          ...FALLBACK_LANGUAGE,
                          code,
                          name: getAutonym(code, settingsName),
                      };
            });

            const dbSystem =
                dbLanguages.find((lang) => lang.code === systemLanguageCode) ??
                dbLanguages.find((lang) => lang.isdefault);
            if (dbSystem) {
                systemLanguage.value = {
                    ...dbSystem,
                    name: getAutonym(dbSystem.code, dbSystem.name),
                };
            }

            // Initial language priority:
            // 1. django_language cookie (user's previous explicit choice)
            // 2. System language (LANGUAGE_CODE), if enabled
            // 3. First available language
            const cookieCode = Cookies.get("django_language");
            const cookieMatch = cookieCode
                ? availableLanguages.value.find(
                      (lang) => lang.code === cookieCode,
                  )
                : undefined;
            const systemMatch = availableLanguages.value.find(
                (lang) => lang.code === systemLanguageCode,
            );
            const initial =
                cookieMatch ?? systemMatch ?? availableLanguages.value[0];

            if (initial) {
                selectedLanguage.value = initial;
                if (gettext.current !== initial.code) {
                    gettext.current = initial.code;
                }
            }
        } catch {
            // Keep placeholder Language objects if fetch fails.
        }
    }

    return {
        selectedLanguage,
        systemLanguage,
        availableLanguages,
        setSelectedLanguage,
        initialize,
    };
});
