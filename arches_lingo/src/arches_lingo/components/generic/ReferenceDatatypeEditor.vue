<script setup lang="ts">
// import { computed, inject, toRef } from "vue";
import { computed, toRef } from "vue";
import Select from "primevue/select";
// import { getItemLabel } from "@/arches_vue_utils/utils.ts";
// import { systemLanguageKey } from "@/arches_references/constants.ts";

import type { ControlledListItem } from "@/arches_lingo/types";
// import type { Language } from "@/arches_vue_utils/types.ts";

// const systemLanguage = inject(systemLanguageKey) as Language;

const props = withDefaults(
    defineProps<{
        val?: ControlledListItem;
        options?: ControlledListItem[];
    }>(),
    {
        options: () => [],
    },
);

console.log(props);

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
// const getOptionLabels = (value) => {
//     return getItemLabel(value, selectedLanguage.value.code, systemLanguage.code)
//         .value;
// };
// :optionLabel="getOptionLabels"
</script>
<template>
    <Select
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
