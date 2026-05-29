import { ref } from "vue";
import { defineStore } from "pinia";

export const useConceptImagesEditorStore = defineStore(
    "conceptImagesEditor",
    () => {
        const targetDigitalObjectResourceInstanceId = ref<string | undefined>(
            undefined,
        );

        return { targetDigitalObjectResourceInstanceId };
    },
);
