import { defineComponent, h, ref } from "vue";

import { mount } from "@vue/test-utils";
import { afterEach, describe, expect, it, vi } from "vitest";
import { EventBus } from "@primeuix/utils/eventbus";

import { useAccessibleToasts } from "@/arches_lingo/composables/useAccessibleToasts.ts";

import type { ToastMessageOptions } from "primevue/toast";

const isAccessibilityMode = ref(true);

vi.mock("@/arches_lingo/stores/useAppSettingsStore.ts", () => ({
    useAppSettingsStore: () => ({ isAccessibilityMode }),
}));

vi.mock("primevue/toasteventbus", () => ({ default: EventBus() }));

async function addToast(message: ToastMessageOptions) {
    const { default: ToastEventBus } = await import("primevue/toasteventbus");
    (
        ToastEventBus as unknown as {
            emit: (event: string, payload: ToastMessageOptions) => void;
        }
    ).emit("add", message);
    return message;
}

function mountWithAccessibleToasts() {
    return mount(
        defineComponent({
            setup() {
                useAccessibleToasts();
                return () => h("div");
            },
        }),
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
});
