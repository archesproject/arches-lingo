import { ref } from "vue";

import { mount } from "@vue/test-utils";
import PrimeVue from "primevue/config";
import { describe, expect, it, vi } from "vitest";

import ReconciliationWorksheetExportButton from "@/arches_lingo/components/generic/ReconciliationWorksheetExportButton.vue";

const downloadWorksheet = vi.fn();
const isDownloading = ref(false);

vi.mock(
    "@/arches_lingo/composables/useReconciliationWorksheetDownload.ts",
    () => ({
        useReconciliationWorksheetDownload: () => ({
            isDownloading,
            downloadWorksheet,
        }),
    }),
);

describe("ReconciliationWorksheetExportButton", () => {
    it("downloads the worksheet for its scope, showing progress meanwhile", async () => {
        const wrapper = mount(ReconciliationWorksheetExportButton, {
            props: { scope: { concept_set_id: 3 } },
            global: { plugins: [PrimeVue] },
        });

        await wrapper.find("button").trigger("click");
        isDownloading.value = true;
        await wrapper.vm.$nextTick();

        expect(downloadWorksheet).toHaveBeenCalledWith({ concept_set_id: 3 });
        expect(wrapper.find("button").text()).toBe("Reconciliation worksheet");
        expect(wrapper.find("button").attributes("data-p-disabled")).toBe(
            "true",
        );
    });
});
