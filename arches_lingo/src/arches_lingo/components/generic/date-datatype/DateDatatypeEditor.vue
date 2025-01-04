<script setup lang="ts">
import { toRef, watch } from "vue";

import DatePicker from "primevue/datepicker";

const props = defineProps<{
    value: string | undefined;
    dateFormat: string;
}>();

const emit = defineEmits(["update"]);

const modelValue = toRef(props.value);

watch(
    () => props.value,
    (newValue) => {
        modelValue.value = newValue;
    },
);
</script>

<template>
    <DatePicker
        v-model="modelValue"
        icon-display="input"
        :date-format="dateFormat"
        show-icon
        @update:model-value="() => emit('update', modelValue)"
    />
</template>
