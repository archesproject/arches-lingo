import { defineComponent, h, nextTick, ref } from "vue";

import { mount } from "@vue/test-utils";
import { afterEach, describe, expect, it, vi } from "vitest";
import PrimeVue from "primevue/config";
import Toast from "primevue/toast";

import {
    TOAST_MESSAGE_PASS_THROUGH,
    useAccessibleToasts,
} from "@/arches_lingo/composables/useAccessibleToasts.ts";

import type { ToastMessageOptions } from "primevue/toast";

const isAccessibilityMode = ref(true);

vi.mock("@/arches_lingo/stores/useAppSettingsStore.ts", () => ({
    useAppSettingsStore: () => ({ isAccessibilityMode }),
}));

async function addToast(message: ToastMessageOptions) {
    const { default: ToastEventBus } = await import("primevue/toasteventbus");
    (
        ToastEventBus as unknown as {
            emit: (event: string, payload: ToastMessageOptions) => void;
        }
    ).emit("add", message);
    return message;
}

// Like ArchesLingo: the composable's owner renders <Toast> as a child.
function mountWithAccessibleToasts() {
    return mount(
        defineComponent({
            setup() {
                useAccessibleToasts();
                return () =>
                    h(Toast, { pt: { message: TOAST_MESSAGE_PASS_THROUGH } });
            },
        }),
        {
            attachTo: document.body,
            global: {
                plugins: [PrimeVue],
                stubs: { transition: false, "transition-group": false },
            },
        },
    );
}

describe("useAccessibleToasts", () => {
    afterEach(() => {
        isAccessibilityMode.value = true;
    });

    it("keeps errors and detailed toasts open in accessibility mode", async () => {
        const wrapper = mountWithAccessibleToasts();

        const error = await addToast({ severity: "error", life: 8000 });
        const detailed = await addToast({
            severity: "success",
            detail: "2 skipped",
            life: 5000,
        });
        const brief = await addToast({ severity: "success", life: 5000 });

        expect(error.life).toBe(0);
        expect(detailed.life).toBe(0);
        expect(brief.life).toBe(5000);
        wrapper.unmount();
    });

    it("leaves every toast timed outside accessibility mode", async () => {
        isAccessibilityMode.value = false;
        const wrapper = mountWithAccessibleToasts();

        const error = await addToast({ severity: "error", life: 8000 });

        expect(error.life).toBe(8000);
        wrapper.unmount();
    });

    it("focuses each new toast's own close button, not an older one", async () => {
        const opener = document.createElement("button");
        document.body.append(opener);
        opener.focus();
        const wrapper = mountWithAccessibleToasts();

        await addToast({ severity: "error", summary: "First" });
        await nextTick();
        const firstToast = document.activeElement?.closest("[data-toast-id]");
        expect(firstToast?.textContent).toContain("First");

        await addToast({ severity: "error", summary: "Second" });
        await nextTick();
        const secondToast = document.activeElement?.closest("[data-toast-id]");
        expect(secondToast?.textContent).toContain("Second");

        wrapper.unmount();
        opener.remove();
    });
});
