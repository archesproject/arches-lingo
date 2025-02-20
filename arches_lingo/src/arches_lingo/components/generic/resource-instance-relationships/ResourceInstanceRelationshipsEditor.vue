<script setup lang="ts">
import { computed, toRef, ref, watch } from "vue";
import MultiSelect from "primevue/multiselect";
import type { ResourceInstanceReference } from "@/arches_lingo/types";
import { useGettext } from "vue3-gettext";

const { $gettext } = useGettext();

const props = withDefaults(
    defineProps<{
        val?: string[];
        options?: ResourceInstanceReference[];
        ptAriaLabeledBy?: string;
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
        console.log("value", value);
        emit("update", value);
    },
});

const primeVuePickerVal = ref(value.value);
watch(primeVuePickerVal, (newVal) => {
    value.value = newVal;
});
</script>
<template>
    <MultiSelect
        v-model="primeVuePickerVal"
        :show-toggle-all="!!options?.length"
        :options
        option-label="display_value"
        option-value="resourceId"
        :pt="{
            emptyMessage: { style: { fontFamily: 'sans-serif' } },
            option: { style: { fontFamily: 'sans-serif' } },
        }"
        :placeholder="$gettext('Select Resources')"
        :aria-labelledby="props.ptAriaLabeledBy"
    />
</template>
