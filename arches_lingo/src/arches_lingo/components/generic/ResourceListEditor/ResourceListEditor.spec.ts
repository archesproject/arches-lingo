import { defineComponent, h, inject, nextTick, reactive, ref } from "vue";
import { flushPromises, mount } from "@vue/test-utils";

import PrimeVue from "primevue/config";
import DataTable from "primevue/datatable";
import ToastService from "primevue/toastservice";

import ResourceListEditor from "@/arches_lingo/components/generic/ResourceListEditor/ResourceListEditor.vue";
import { useEditorDirtyState } from "@/arches_lingo/composables/useEditorDirtyState.ts";

import type { Ref } from "vue";
import type { ResourceSummary } from "@/arches_lingo/types";

const confirmRequire = vi.fn();

function passThroughGettext(text: string) {
    return text;
}

vi.mock("vue3-gettext", () => ({
    useGettext: () => ({
        $gettext: passThroughGettext,
        $ngettext: passThroughGettext,
        interpolate: passThroughGettext,
    }),
}));

vi.mock("primevue/useconfirm", () => ({
    useConfirm: () => ({ require: confirmRequire, close: vi.fn() }),
}));

vi.mock("@/arches_lingo/composables/useMediaQuery.ts", () => ({
    useMediaQuery: () => ref(false),
}));

vi.mock("@/arches_lingo/api.ts", () => ({
    deleteLingoResource: vi.fn(),
    fetchResourceReferenceCount: vi.fn(),
}));

function buildResource(id: string): ResourceSummary {
    return {
        resourceinstanceid: id,
        display_name: `Resource ${id}`,
        graph_slug: "textual_work",
        graph_name: "Textual Work",
    } as ResourceSummary;
}

const resources = [buildResource("first"), buildResource("second")];

// Stands in for ResourceNameCard: registers a form facade with the
// surrounding ComponentEditor, and exposes a way to make it dirty.
const markFakeFormDirty = ref<() => void>(() => undefined);
const FakeNameForm = defineComponent({
    setup() {
        const componentEditorFormRef = inject<Ref<unknown>>(
            "componentEditorFormRef",
        );
        const formFacade = reactive({
            states: {} as Record<string, { dirty: boolean }>,
            submit: vi.fn(),
        });
        if (componentEditorFormRef) {
            componentEditorFormRef.value = formFacade;
        }
        markFakeFormDirty.value = () => {
            formFacade.states = { name: { dirty: true } };
        };
        return () => h("input", { id: "name" });
    },
});

// The "Add" action the page renders in the list-actions slot.
let openBlankEditorFromSlot: () => void = () => undefined;

async function mountEditor() {
    const wrapper = mount(ResourceListEditor, {
        props: {
            pageTitle: "Sources",
            fetchResources: async () => ({
                results: resources,
                count: resources.length,
            }),
            editorEnabled: true,
        },
        slots: {
            editor: () => h(FakeNameForm),
            "list-actions": (slotProps: { openBlankEditor: () => void }) => {
                openBlankEditorFromSlot = slotProps.openBlankEditor;
                return h("span");
            },
        },
        global: {
            plugins: [PrimeVue, ToastService],
            mocks: {
                $gettext: passThroughGettext,
                $ngettext: passThroughGettext,
            },
        },
        attachTo: document.body,
    });
    await flushPromises();
    return wrapper;
}

describe("ResourceListEditor unsaved changes", () => {
    beforeEach(() => {
        confirmRequire.mockReset();
        useEditorDirtyState().isEditorDirty.value = false;
        useEditorDirtyState().isUnsavedChangesConfirmOpen.value = false;
    });

    async function openFirstRow(
        wrapper: Awaited<ReturnType<typeof mountEditor>>,
    ) {
        wrapper
            .findComponent(DataTable)
            .vm.$emit("row-select", { data: resources[0] });
        await flushPromises();
    }

    async function makeFormDirty() {
        markFakeFormDirty.value();
        await nextTick();
        await nextTick();
    }

    function pressEscape() {
        window.dispatchEvent(
            new KeyboardEvent("keydown", { key: "Escape", bubbles: true }),
        );
    }

    function acceptOpenConfirm() {
        confirmRequire.mock.calls[0][0].accept();
    }

    it("asks before switching rows while the editor is dirty", async () => {
        const wrapper = await mountEditor();
        await openFirstRow(wrapper);
        await makeFormDirty();

        expect(useEditorDirtyState().isEditorDirty.value).toBe(true);

        wrapper
            .findComponent(DataTable)
            .vm.$emit("row-select", { data: resources[1] });
        await flushPromises();

        expect(confirmRequire).toHaveBeenCalledTimes(1);
        wrapper.unmount();
    });

    it("lets the page reset for a new resource only after discarding", async () => {
        const wrapper = await mountEditor();
        await openFirstRow(wrapper);
        await makeFormDirty();

        openBlankEditorFromSlot();
        await flushPromises();

        expect(confirmRequire).toHaveBeenCalledTimes(1);
        expect(wrapper.emitted("create-resource")).toBeUndefined();

        acceptOpenConfirm();
        await flushPromises();

        expect(wrapper.emitted("create-resource")).toHaveLength(1);
        wrapper.unmount();
    });

    it("closes a clean editor on Escape", async () => {
        const wrapper = await mountEditor();
        await openFirstRow(wrapper);
        expect(wrapper.find(".editor-panel").exists()).toBe(true);

        pressEscape();
        await flushPromises();

        expect(confirmRequire).toHaveBeenCalledTimes(0);
        expect(wrapper.find(".editor-panel").exists()).toBe(false);
        wrapper.unmount();
    });

    it("asks before closing a dirty editor on Escape", async () => {
        const wrapper = await mountEditor();
        await openFirstRow(wrapper);
        await makeFormDirty();

        pressEscape();
        await flushPromises();

        expect(confirmRequire).toHaveBeenCalledTimes(1);
        expect(wrapper.find(".editor-panel").exists()).toBe(true);

        acceptOpenConfirm();
        await flushPromises();

        expect(wrapper.find(".editor-panel").exists()).toBe(false);
        wrapper.unmount();
    });

    it("stops listening for Escape once unmounted", async () => {
        const wrapper = await mountEditor();
        await openFirstRow(wrapper);
        await makeFormDirty();
        wrapper.unmount();
        useEditorDirtyState().isEditorDirty.value = true;

        pressEscape();

        expect(confirmRequire).toHaveBeenCalledTimes(0);
    });
});
