import { createPinia, setActivePinia } from "pinia";
import PrimeVue from "primevue/config";
import { flushPromises, mount } from "@vue/test-utils";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import ReconciliationEndpointPanel from "@/arches_lingo/components/dashboard/ReconciliationEndpointPanel.vue";

import { useAppSettingsStore } from "@/arches_lingo/stores/useAppSettingsStore.ts";

import type { VueWrapper } from "@vue/test-utils";
import type { AppSettings } from "@/arches_lingo/types.ts";

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

function mountPanel(settingsOverrides: Partial<AppSettings>): VueWrapper {
    useAppSettingsStore().settings = {
        allow_anonymous_access: false,
        reconciliation_enabled: true,
        reconciliation_service_url: GLOBAL_SERVICE_URL,
        scheme_reconciliation_service_url_template:
            "https://lingo.example.org/api/lingo/schemes/{scheme_identifier}/reconcile",
        public_server_address: "https://lingo.example.org/",
        arches_version: "8.1",
        lingo_version: "1.2",
        ...settingsOverrides,
    };
    return mount(ReconciliationEndpointPanel, {
        global: {
            plugins: [PrimeVue],
            mocks: { $gettext: (text: string) => text },
        },
    });
}

function displayedServiceUrl(wrapper: VueWrapper): string {
    return (wrapper.find("input").element as HTMLInputElement).value;
}

describe("ReconciliationEndpointPanel", () => {
    beforeEach(() => {
        setActivePinia(createPinia());
        toastAdd.mockReset();
    });

    afterEach(() => {
        Object.defineProperty(navigator, "clipboard", {
            value: undefined,
            configurable: true,
        });
    });

    it("renders nothing while the reconciliation service is disabled", () => {
        const wrapper = mountPanel({
            reconciliation_enabled: false,
            reconciliation_service_url: null,
            scheme_reconciliation_service_url_template: null,
        });

        expect(wrapper.find(".dashboard-section").exists()).toBe(false);
    });

    it("offers the global service", () => {
        const wrapper = mountPanel({});

        expect(displayedServiceUrl(wrapper)).toBe(GLOBAL_SERVICE_URL);
        expect(wrapper.find(".hint-text").text()).toContain(
            "against published schemes",
        );
    });

    it("copies the service URL", async () => {
        const writeText = vi.fn().mockResolvedValue(undefined);
        Object.defineProperty(navigator, "clipboard", {
            value: { writeText },
            configurable: true,
        });
        const wrapper = mountPanel({});

        await wrapper.find("button").trigger("click");
        await flushPromises();

        expect(writeText).toHaveBeenCalledWith(GLOBAL_SERVICE_URL);
        expect(toastAdd).toHaveBeenCalledWith(
            expect.objectContaining({ severity: "success" }),
        );
    });

    it("names the region by its heading and describes the URL by the hint", () => {
        const wrapper = mountPanel({});
        const heading = wrapper.find("h2");
        const hint = wrapper.find(".hint-text");

        expect(
            wrapper.find(".dashboard-section").attributes("aria-labelledby"),
        ).toBe(heading.attributes("id"));
        expect(wrapper.find("input").attributes("aria-describedby")).toBe(
            hint.attributes("id"),
        );
    });
});
