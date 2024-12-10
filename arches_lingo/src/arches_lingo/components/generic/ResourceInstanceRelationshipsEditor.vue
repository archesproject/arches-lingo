<script setup lang="ts">
import { computed, toRefs } from "vue";
import MultiSelect from "primevue/multiselect";
import type { ResourceInstanceReference } from "@/arches_lingo/types";

const props = defineProps<{
    val?: string[];
    options?: ResourceInstanceReference[];
}>();

const emit = defineEmits(["update"]);

const propRefs = toRefs(props);

const value = computed({
    get() {
        return propRefs.val.value;
    },
    set(value) {
        emit("update", value);
    },
});
</script>
<template>
    <div>
        <MultiSelect
            v-model="value"
            :options="props.options"
            option-label="display_value"
            option-value="resourceId"
            placeholder="Select Resources"
        />
    </div>
</template>
