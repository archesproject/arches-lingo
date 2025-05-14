<script setup lang="ts">
import arches from "arches";
import { useGettext } from "vue3-gettext";

import Button from "primevue/button";

import { SECONDARY } from "@/arches_lingo/constants.ts";

const { $gettext } = useGettext();
</script>

<template>
    <div style="display: flex; justify-content: space-between;">
        <Button
            as="a"
            class="login-action"
            :label="$gettext('Register')"
            :href="arches.urls.signup"
            :severity="SECONDARY"
            :outlined="true"
        />
        <Button
            as="a"
            class="login-action"
            :label="$gettext('Multi-factor login')"
            :href="arches.urls.auth + '?next=/'"
            :severity="SECONDARY"
            :outlined="true"
        />
    </div>
</template>

<style scoped>
    :deep(.login-action) {
        border-radius: 2px;
        text-decoration: none;
        min-width: 10rem;
    }

    :deep(.p-button-outlined.p-button-secondary:not(:disabled):hover) {
        color: var(--p-primary-contrast-color);
        background: var(--p-primary-active-color);
        border-color: var(--p-primary-active-color);
    }
</style>
