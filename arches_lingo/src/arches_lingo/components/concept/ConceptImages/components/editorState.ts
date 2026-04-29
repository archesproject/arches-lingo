import { ref } from "vue";

/**
 * Module-level reactive state shared between ConceptImagesViewer and
 * ConceptImagesEditor to coordinate which digital object should be loaded.
 *
 * Replaces the previous document-level CustomEvent coordination which was
 * susceptible to race conditions when events fired out of order.
 */
export const targetDigitalObjectResourceInstanceId = ref<string | undefined>(
    undefined,
);
