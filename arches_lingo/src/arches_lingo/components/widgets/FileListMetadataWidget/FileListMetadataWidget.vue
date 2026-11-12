<script setup lang="ts">
// Lingo 1.2 backport of core 8.2's FileListWidget metadata editing
// (arches#13094). arches-vue-components 2.0.x has no metadata inputs, so this
// directory carries a PrimeVue port of the 8.2 editor.
//
// Remove this directory when Lingo moves to Arches 8.2 (Lingo 1.3), and render
// the node with GenericWidget instead: it takes the same cardXNodeXWidgetData,
// metadata-language-code and update:metadata-language-code.
import { ref } from "vue";

import GenericFormField from "@/arches_vue_components/generics/GenericWidget/components/GenericFormField.vue";
import FileListMetadataWidgetEditor from "@/arches_lingo/components/widgets/FileListMetadataWidget/components/FileListMetadataWidgetEditor.vue";

import type { AliasedNodeData } from "@/arches_vue_components/types.ts";
import type {
    FileListAliasedNodeData,
    FileListCardXNodeXWidgetData,
} from "@/arches_lingo/components/widgets/FileListMetadataWidget/types.ts";

const {
    aliasedNodeData = null,
    cardXNodeXWidgetData,
    isDirty = false,
    metadataLanguageCode = undefined,
    nodeAlias,
} = defineProps<{
    aliasedNodeData?: FileListAliasedNodeData | null;
    // Required, unlike GenericWidget: the caller fetches it and flips the
    // metadata visibility bits on a copy.
    cardXNodeXWidgetData: FileListCardXNodeXWidgetData;
    isDirty?: boolean;
    metadataLanguageCode?: string;
    nodeAlias: string;
}>();

const emit = defineEmits<{
    "update:isDirty": [isDirty: boolean];
    "update:aliasedNodeData": [aliasedNodeData: FileListAliasedNodeData];
    "update:metadataLanguageCode": [languageCode: string, fileIndex: number];
}>();

const resolvedInitialValue = ref<FileListAliasedNodeData | null>(null);

function onUpdateAliasedNodeData(
    updatedAliasedNodeData: FileListAliasedNodeData,
    notifyFormField: (aliasedNodeData: AliasedNodeData) => void,
) {
    notifyFormField(updatedAliasedNodeData);
    emit("update:aliasedNodeData", updatedAliasedNodeData);
}
</script>

<template>
    <GenericFormField
        v-slot="{ onUpdateAliasedNodeData: notifyFormField }"
        :is-dirty="isDirty"
        :initial-value="resolvedInitialValue"
        :node-alias="nodeAlias"
        @update:is-dirty="emit('update:isDirty', $event)"
    >
        <FileListMetadataWidgetEditor
            :aliased-node-data="aliasedNodeData"
            :card-x-node-x-widget-data="cardXNodeXWidgetData"
            :metadata-language-code="metadataLanguageCode"
            @initialized="resolvedInitialValue = $event"
            @update:aliased-node-data="
                onUpdateAliasedNodeData($event, notifyFormField)
            "
            @update:metadata-language-code="
                (languageCode, fileIndex) =>
                    emit('update:metadataLanguageCode', languageCode, fileIndex)
            "
        />
    </GenericFormField>
</template>
