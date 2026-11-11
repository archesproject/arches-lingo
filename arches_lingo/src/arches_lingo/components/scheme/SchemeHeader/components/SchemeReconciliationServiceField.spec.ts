import { createPinia, setActivePinia } from "pinia";
import PrimeVue from "primevue/config";
import { flushPromises, mount } from "@vue/test-utils";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import SchemeReconciliationServiceField from "@/arches_lingo/components/scheme/SchemeHeader/components/SchemeReconciliationServiceField.vue";

import { useAppSettingsStore } from "@/arches_lingo/stores/useAppSettingsStore.ts";

import type { VueWrapper } from "@vue/test-utils";

const GLOBAL_SERVICE_URL = "https://lingo.example.org/api/lingo/reconcile";

const toastAdd = vi.fn();

vi.mock("primevue/usetoast", () => ({
    useToast: () => ({ add: toastAdd }),
}));

vi.mock("vue3-gettext", () => ({
    useGettext: () => ({
        $gettext: (text: string) => text,
        interpolate: (text: string, values: Record<string, string>) =>
            text.replace(
                /%\{(\w+)\}/g,
                (_placeholder, valueName: string) => values[valueName],
            ),
    }),
}));

function mountField(props: {
    schemeIdentifier: string | undefined;
    schemeName: string | undefined;
}): VueWrapper {
    useAppSettingsStore().settings = {
        allow_anonymous_access: false,
        reconciliation_enabled: true,
        reconciliation_service_url: GLOBAL_SERVICE_URL,
        scheme_reconciliation_service_url_template:
            "https://lingo.example.org/api/lingo/schemes/{scheme_identifier}/reconcile",
        public_server_address: "https://lingo.example.org/",
        arches_version: "8.1",
        lingo_version: "1.2",
    };
    return mount(SchemeReconciliationServiceField, {
        props,
        attachTo: document.body,
        global: {
            plugins: [PrimeVue],
            mocks: { $gettext: (text: string) => text },
        },
    });
}

function usageHintToggle(wrapper: VueWrapper) {
    return wrapper.find(".usage-hint-toggle");
}

function describedUsageHint(wrapper: VueWrapper): string {
    const hintId = usageHintToggle(wrapper).attributes("aria-describedby");
    return wrapper.find(`[id="${hintId}"]`).text();
}

describe("SchemeReconciliationServiceField", () => {
    let wrapper: VueWrapper;

    beforeEach(() => {
        setActivePinia(createPinia());
        toastAdd.mockReset();
    });

    afterEach(() => {
        wrapper.unmount();
        Object.defineProperty(navigator, "clipboard", {
            value: undefined,
            configurable: true,
        });
    });

    it("offers and copies a scheme's own service when the scheme has an identifier", async () => {
        const writeText = vi.fn().mockResolvedValue(undefined);
        Object.defineProperty(navigator, "clipboard", {
            value: { writeText },
            configurable: true,
        });
        const schemeServiceUrl =
            "https://lingo.example.org/api/lingo/schemes/aat/reconcile";
        wrapper = mountField({
            schemeIdentifier: "aat",
            schemeName: undefined,
        });

        expect(wrapper.find(".header-item-value").text()).toBe(
            schemeServiceUrl,
        );
        await wrapper.find(".copy-button").trigger("click");
        await flushPromises();

        expect(writeText).toHaveBeenCalledWith(schemeServiceUrl);
    });

    it("falls back to the global service, naming the scheme to choose as the type", () => {
        wrapper = mountField({
            schemeIdentifier: "getty.aat",
            schemeName: "Getty AAT",
        });

        expect(wrapper.find(".header-item-value").text()).toBe(
            GLOBAL_SERVICE_URL,
        );
        expect(describedUsageHint(wrapper)).toContain(
            'choose "Getty AAT" as the type',
        );
    });

    it("describes the info button by the hint and shows it on click", async () => {
        wrapper = mountField({
            schemeIdentifier: "aat",
            schemeName: undefined,
        });
        const hintId = usageHintToggle(wrapper).attributes("aria-describedby");

        expect(wrapper.find(`[id="${hintId}"]`).attributes()).toHaveProperty(
            "hidden",
        );
        expect(document.querySelector(".usage-hint")).toBeNull();

        await usageHintToggle(wrapper).trigger("click");
        await flushPromises();

        const shownHint = document.querySelector(".usage-hint");
        expect(shownHint?.textContent).toBe(describedUsageHint(wrapper));
        expect(
            Boolean(shownHint?.closest("[aria-hidden='true']")),
            "screen readers already have the hint through aria-describedby",
        ).toBe(true);
    });
});
