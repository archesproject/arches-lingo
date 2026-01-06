<script setup lang="ts">
import { generateArchesURL } from "@/arches/utils/generate-arches-url.ts";
const { file } = defineProps<{
    file: {
        fileid: string;
        name: string;
        url: string;
    };
}>();

const fileURL = generateArchesURL("arches:temp_file", { file_id: file.fileid });
</script>

<template>
    <a
        :href="fileURL"
        target="_blank"
        >{{ file.name }}</a
    >
</template>
