<script setup lang="ts">
import NonLocalizedStringViewer from "@/arches_lingo/components/generic/NonLocalizedStringViewer.vue";
import NonLocalizedStringEditor from "@/arches_lingo/components/generic/NonLocalizedStringEditor.vue";
import type { DataComponentMode } from "@/arches_lingo/types.ts";
import { EDIT, VIEW } from "@/arches_lingo/constants.ts";

const props = defineProps<{ mode?: DataComponentMode; value?: string }>();
const emits = defineEmits(["update"]);
const onUpdate = (val: string) => {
    emits("update", val);
};
</script>
<template>
    <div>
        <div v-if="!props.mode || props.mode === VIEW">
            <NonLocalizedStringViewer :value="props.value ?? ''" />
        </div>
        <div v-if="props.mode === EDIT">
            <NonLocalizedStringEditor
                :value="props.value ?? ''"
                @update="onUpdate"
            />
        </div>
    </div>
</template>
