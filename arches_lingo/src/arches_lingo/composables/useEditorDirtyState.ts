import { ref } from "vue";

// Module-level singleton: tracks whether the currently active editor form has
// unsaved changes. ComponentEditor writes to this; any component that triggers
// navigation (ComponentManager, ConceptTree, etc.) reads from it to decide
// whether to prompt the user before proceeding.
const isEditorDirty = ref(false);

export function useEditorDirtyState() {
    return { isEditorDirty };
}
