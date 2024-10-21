<script setup lang="ts">
import type { Concept } from "@/arches_lingo/types";

const { concept } = defineProps<{ concept: Concept }>();
</script>

<template>
    {{ concept }}
</template>
