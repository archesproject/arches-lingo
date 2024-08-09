<script setup lang="ts">
import arches from "arches";
import { useGettext } from "vue3-gettext";

import Button from "primevue/button";

const { $gettext } = useGettext();
</script>

<template>
    <div style="display: flex; justify-content: space-between; width: 30%">
        <Button
            as="a"
            :label="$gettext('Register')"
            :href="arches.urls.signup"
        />
        <Button
            as="a"
            :label="$gettext('Multi-factor login')"
            :href="arches.urls.auth"
        />
    </div>
</template>
