<script setup lang="ts">
import { computed, inject, ref } from "vue";
import Select from "primevue/select";
import MultiSelect from "primevue/multiselect";

import { systemLanguageKey } from "@/arches_lingo/constants.ts";
import { PREF_LABEL } from "@/arches_vue_utils/constants.ts";

import type { ControlledListItem } from "@/arches_lingo/types";
import type { Language } from "@/arches_vue_utils/types.ts";

const systemLanguage = inject(systemLanguageKey) as Language;
const emit = defineEmits(["update"]);
const props = withDefaults(
    defineProps<{
        value?: ControlledListItem[];
        options?: ControlledListItem[];
        multiValue?: boolean;
    }>(),
    {
        value: () => [],
        options: () => [],
    },
);

const uriRef = ref(extractURI(props.value));
const val = computed({
    get() {
        return uriRef.value;
    },
    set(newVal) {
        uriRef.value = newVal;
        if (!props.multiValue) {
            const item = props.options?.find((item) => item.uri === newVal);
            emit("update", item ? [item] : []);
        } else {
            const items = props.options?.filter((item) =>
                newVal.includes(item.uri),
            );
            emit("update", items ?? []);
        }
    },
});

function extractURI(item: ControlledListItem[]): string | string[] {
    if (item && !props.multiValue) {
        return item[0].uri;
    } else if (item && props.multiValue) {
        return item.map((item) => item.uri);
    } else {
        return [];
    }
}

function getOptionLabels(item: ControlledListItem): string {
    const prefLabels = item.labels.filter(
        (label) => label.valuetype_id === PREF_LABEL,
    );
    const optionLabel =
        prefLabels.find(
            (label) => label.language_id === systemLanguage?.code,
        ) || prefLabels[0];
    return optionLabel?.value ?? "";
}
</script>

<template>
    <Select
        v-model="val"
        v-if:="!props.multiValue"
        :show-toggle-all="options?.length"
        :options
        :option-label="getOptionLabels"
        option-value="uri"
        :pt="{
            emptyMessage: { style: { fontFamily: 'sans-serif' } },
            option: { style: { fontFamily: 'sans-serif' } },
        }"
        :placeholder="$gettext('Select References')"
    />
    <MultiSelect
        v-if="props.multiValue"
        v-model="val"
        :show-toggle-all="options?.length"
        :options
        :option-label="getOptionLabels"
        option-value="uri"
        :pt="{
            emptyMessage: { style: { fontFamily: 'sans-serif' } },
            option: { style: { fontFamily: 'sans-serif' } },
        }"
        :placeholder="$gettext('Select References')"
    />
</template>
