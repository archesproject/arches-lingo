<script setup lang="ts">
import NonLocalizedStringViewer from "@/arches_lingo/components/generic/non-localized-string/NonLocalizedStringViewer.vue";
import NonLocalizedStringEditor from "@/arches_lingo/components/generic/non-localized-string/NonLocalizedStringEditor.vue";
import type { DataComponentMode } from "@/arches_lingo/types.ts";
import { EDIT, VIEW } from "@/arches_lingo/constants.ts";

const { mode = VIEW } = defineProps<{
    mode?: DataComponentMode;
    value?: string;
}>();
const emits = defineEmits(["update"]);
const onUpdate = (val: string) => {
    emits("update", val);
};
</script>
<template>
    <div>
        <div v-if="mode === VIEW">
            <NonLocalizedStringViewer :value="value ?? ''" />
        </div>
        <div v-if="mode === EDIT">
            <NonLocalizedStringEditor
                :value="value ?? ''"
                @update="onUpdate"
            />
        </div>
    </div>
</template>
