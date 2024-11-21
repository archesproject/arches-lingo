<script setup lang="ts">
import type {
    DataComponentMode,
    ResourceInstanceReference,
} from "@/arches_lingo/types";
import ResourceInstanceRelationshipsViewer from "@/arches_lingo/components/generic/ResourceInstanceRelationshipsViewer.vue";
import ResourceInstanceRelationshipsEditor from "@/arches_lingo/components/generic/ResourceInstanceRelationshipsEditor.vue";
import { EDIT, VIEW } from "@/arches_lingo/constants.ts";

const props = defineProps<{
    mode?: DataComponentMode;
    value?: ResourceInstanceReference[];
    options?: ResourceInstanceReference[];
}>();

const emits = defineEmits(["update"]);

function onUpdate(val: string[]) {
    emits("update", val);
}
</script>
<template>
    <div>
        <div v-if="!props.mode || props.mode === VIEW">
            <ResourceInstanceRelationshipsViewer :value="props.value" />
        </div>
        <div v-if="props.mode === EDIT">
            <ResourceInstanceRelationshipsEditor
                :options="props.options"
                :val="props.value?.map((x) => x.resourceId)"
                @update="onUpdate"
            />
        </div>
    </div>
</template>
