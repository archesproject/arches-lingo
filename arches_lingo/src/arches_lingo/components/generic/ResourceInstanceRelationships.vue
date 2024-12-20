<script setup lang="ts">
import ResourceInstanceRelationshipsViewer from "@/arches_lingo/components/generic/ResourceInstanceRelationshipsViewer.vue";
import ResourceInstanceRelationshipsEditor from "@/arches_lingo/components/generic/ResourceInstanceRelationshipsEditor.vue";
import { EDIT, VIEW } from "@/arches_lingo/constants.ts";
import type {
    DataComponentMode,
    ResourceInstanceReference,
} from "@/arches_lingo/types";

const { mode = EDIT } = defineProps<{
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
    <div v-if="mode === VIEW">
        <ResourceInstanceRelationshipsViewer :value="value" />
    </div>
    <div v-if="mode === EDIT">
        <ResourceInstanceRelationshipsEditor
            :options="options"
            :val="
                value?.map((referenceValue) => referenceValue.resourceId) ?? []
            "
            @update="onUpdate"
        />
    </div>
</template>
