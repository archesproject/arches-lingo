<script setup lang="ts">
import { computed } from "vue";

import { dataIsScheme } from "@/arches_lingo/utils.ts";

import type { Concept, Scheme } from "@/arches_lingo/types";

const props = defineProps<{ labelled: Concept | Scheme }>();

const color = computed(() => {
    if (dataIsScheme(props.labelled)) {
        return "midnightblue";
    }
    return "darkorchid";
});

const letter = computed(() => {
    // not translated...
    if (dataIsScheme(props.labelled)) {
        return "S";
    }
    return "C";
});
</script>

<template>
    <div
        class="circle"
        aria-hidden="true"
    >
        <span class="letter">{{ letter }}</span>
    </div>
</template>

<style scoped>
.circle {
    width: 1.5rem;
    height: 1.5rem;
    min-width: 1.5rem;
    border-radius: 50%;
    background-color: v-bind("color");
    font-weight: 600;
    align-self: center;
    display: grid;
}

.letter {
    text-align: center;
    align-self: center;
    font-size: x-small;
    color: white;
}
</style>
