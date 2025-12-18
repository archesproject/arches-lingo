<script setup lang="ts">
const { file } = defineProps<{
    file: {
        fileid: string;
        name: string;
        url: string;
    };
}>();
</script>

<template>
    <a
        :href="'/temp_file/' + file.fileid"
        target="_blank"
        >{{ file.name }}</a
    >
</template>
