<script setup lang="ts">
import type {
    ControlledListItem,
    DataComponentMode,
} from "@/arches_lingo/types";
import ControlledListItemViewer from "@/arches_lingo/components/generic/controlled-list-item/ControlledListItemViewer.vue";
import { EDIT, VIEW } from "@/arches_lingo/constants.ts";

const { mode = VIEW } = defineProps<{
    mode?: DataComponentMode;
    value?: ControlledListItem | ControlledListItem[];
}>();
defineEmits(["update"]);
</script>
<template>
    <div>
        <div v-if="mode === VIEW">
            <ControlledListItemViewer :value="value" />
        </div>
        <div v-if="mode === EDIT" />
    </div>
</template>
