import { createPinia, setActivePinia } from "pinia";
import PrimeVue from "primevue/config";
import { flushPromises, mount } from "@vue/test-utils";
import { beforeEach, describe, expect, it, vi } from "vitest";

import ReconciliationEndpointPanel from "@/arches_lingo/components/generic/ReconciliationEndpointPanel.vue";

import { useAppSettingsStore } from "@/arches_lingo/stores/useAppSettingsStore.ts";

import type { VueWrapper } from "@vue/test-utils";
import type { AppSettings } from "@/arches_lingo/types.ts";

const GLOBAL_SERVICE_URL = "https://lingo.example.org/api/lingo/reconcile";

const toastAdd = vi.fn();

vi.mock("primevue/usetoast", () => ({
    useToast: () => ({ add: toastAdd }),
}));

vi.mock("@/arches/utils/generate-arches-url.ts", () => ({
    generateArchesURL: (
        _urlName: string,
        urlParameters: { scheme_identifier: string },
    ) => `/api/lingo/schemes/${urlParameters.scheme_identifier}/reconcile`,
}));

function mountPanel(
    settingsOverrides: Partial<AppSettings>,
    props: { schemeIdentifier?: string; schemeName?: string } = {},
): VueWrapper {
    useAppSettingsStore().settings = {
        allow_anonymous_access: false,
        reconciliation_enabled: true,
        reconciliation_service_url: GLOBAL_SERVICE_URL,
        public_server_address: "https://lingo.example.org/",
        arches_version: "8.1",
        lingo_version: "1.2",
        ...settingsOverrides,
    };
    return mount(ReconciliationEndpointPanel, {
        props,
        global: { plugins: [PrimeVue] },
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

    it("renders nothing while the reconciliation service is disabled", () => {
        const wrapper = mountPanel({
            reconciliation_enabled: false,
            reconciliation_service_url: null,
        });

        expect(wrapper.find(".reconciliation-endpoint").exists()).toBe(false);
    });

    it("offers the global service, naming the scheme to choose as the type", () => {
        const wrapper = mountPanel({}, { schemeName: "Test Scheme" });

        expect(displayedServiceUrl(wrapper)).toBe(GLOBAL_SERVICE_URL);
        expect(wrapper.find(".hint").text()).toContain("as the type");
    });

    it("offers a scheme's own service when the scheme has an identifier", () => {
        const wrapper = mountPanel({}, { schemeIdentifier: "aat" });

        expect(displayedServiceUrl(wrapper)).toBe(
            "https://lingo.example.org/api/lingo/schemes/aat/reconcile",
        );
    });

    it("copies the service URL and confirms with a toast", async () => {
        const writeText = vi.fn().mockResolvedValue(undefined);
        Object.assign(navigator, { clipboard: { writeText } });
        const wrapper = mountPanel({});

        await wrapper.find("button").trigger("click");
        await flushPromises();

        expect(writeText).toHaveBeenCalledWith(GLOBAL_SERVICE_URL);
        expect(toastAdd).toHaveBeenCalledWith(
            expect.objectContaining({ severity: "success" }),
        );
    });

    it("reports a failed copy", async () => {
        const writeText = vi.fn().mockRejectedValue(new Error("denied"));
        Object.assign(navigator, { clipboard: { writeText } });
        const wrapper = mountPanel({});

        await wrapper.find("button").trigger("click");
        await flushPromises();

        expect(toastAdd).toHaveBeenCalledWith(
            expect.objectContaining({ severity: "error", detail: "denied" }),
        );
    });
});
