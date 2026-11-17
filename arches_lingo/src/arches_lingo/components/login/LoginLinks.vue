<script setup lang="ts">
import arches from "arches";
import { computed } from "vue";
import { useRoute } from "vue-router";
import { useGettext } from "vue3-gettext";

import Button from "primevue/button";

import { SECONDARY } from "@/arches_lingo/constants.ts";
import { getSafeNextPath } from "@/arches_lingo/utils.ts";

const { $gettext } = useGettext();
const route = useRoute();

// Pass the post-login destination through the MFA flow
const multiFactorLoginUrl = computed(() => {
    const nextPath =
        getSafeNextPath(route.query.next) ??
        getSafeNextPath(route.redirectedFrom?.fullPath) ??
        "/dashboard";
    return `${arches.urls.auth}?next=${encodeURIComponent(nextPath)}`;
});
</script>

<template>
    <div class="link-container">
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
            :href="multiFactorLoginUrl"
            :severity="SECONDARY"
            :outlined="true"
        />
    </div>
</template>

<style scoped>
.link-container {
    display: flex;
    justify-content: space-between;
    gap: 0.5rem;
}

:deep(.login-action) {
    text-decoration: none;
    flex: 1;
}

:deep(.p-button-outlined.p-button-secondary:not(:disabled):hover) {
    color: var(--p-primary-contrast-color);
    background: var(--p-primary-active-color);
    border-color: var(--p-primary-active-color);
}
</style>
