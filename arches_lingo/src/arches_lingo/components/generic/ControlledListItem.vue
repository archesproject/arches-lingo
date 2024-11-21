<script setup lang="ts">
import type {
    ControlledListItem,
    DataComponentMode,
} from "@/arches_lingo/types";
import ControlledListItemViewer from "@/arches_lingo/components/generic/ControlledListItemViewer.vue";
import { EDIT, VIEW } from "@/arches_lingo/constants.ts";

const props = defineProps<{
    mode?: DataComponentMode;
    value?: ControlledListItem;
}>();
defineEmits(["update"]);
</script>
<template>
    <div>
        <div v-if="!props.mode || props.mode === VIEW">
            <ControlledListItemViewer :value="props.value" />
        </div>
        <div v-if="props.mode === EDIT"></div>
    </div>
</template>
