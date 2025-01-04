<script setup lang="ts">
import DateDatatypeViewer from "@/arches_lingo/components/generic/date-datatype/DateDatatypeViewer.vue";
import DateDatatypeEditor from "@/arches_lingo/components/generic/date-datatype/DateDatatypeEditor.vue";

import { EDIT, VIEW } from "@/arches_lingo/constants.ts";

import type { DataComponentMode } from "@/arches_lingo/types.ts";

interface Props {
    dateFormat?: string;
    mode?: DataComponentMode;
    value?: string;
}

withDefaults(defineProps<Props>(), {
    dateFormat: "yy-mm-dd",
    mode: VIEW,
    value: "",
});

const emits = defineEmits(["update"]);

const onUpdate = (val: string) => {
    emits("update", val);
};
</script>

<template>
    <div>
        <div v-if="mode === VIEW">
            <DateDatatypeViewer
                :date-format="dateFormat"
                :value="value"
            />
        </div>
        <div v-if="mode === EDIT">
            <DateDatatypeEditor
                :date-format="dateFormat"
                :value="value"
                @update="onUpdate"
            />
        </div>
    </div>
</template>
