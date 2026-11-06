<script setup lang="ts">
import { useAnnouncer } from "@/arches_lingo/composables/useAnnouncer.ts";

const { politeMessage, assertiveMessage } = useAnnouncer();
</script>

<template>
    <div class="p-hidden-accessible">
        <div role="status">{{ politeMessage }}</div>
        <div role="alert">{{ assertiveMessage }}</div>
    </div>
</template>
