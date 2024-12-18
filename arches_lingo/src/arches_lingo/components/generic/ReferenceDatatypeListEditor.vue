<script setup lang="ts">
import { computed, toRef } from "vue";
import MultiSelect from "primevue/multiselect";
// import { getItemLabel } from "@/arches_vue_utils/utils.ts";

import type { ControlledListItem } from "@/arches_lingo/types";

const props = withDefaults(
    defineProps<{
        val?: ControlledListItem;
        options?: ControlledListItem[];
    }>(),
    {
        options: () => [],
    },
);

const emit = defineEmits(["update"]);

const valRef = toRef(props, "val");

const value = computed({
    get() {
        return valRef.value;
    },
    set(value) {
        emit("update", value);
    },
});
// const getOptionLabels = (option: ControlledListItem) => {
//     return getItemLabel(option);
// };
// :option-label="getOptionLabels"
</script>
<template>
    <MultiSelect
        v-model="value"
        :show-toggle-all="!!options?.length"
        :options
        :pt="{
            emptyMessage: { style: { fontFamily: 'sans-serif' } },
            option: { style: { fontFamily: 'sans-serif' } },
        }"
        :placeholder="$gettext('Select References')"
    />
</template>
