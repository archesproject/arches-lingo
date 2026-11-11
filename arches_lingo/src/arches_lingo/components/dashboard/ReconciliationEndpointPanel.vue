<script setup lang="ts">
import { useId } from "vue";

import Button from "primevue/button";
import InputText from "primevue/inputtext";

import { SECONDARY } from "@/arches_lingo/constants.ts";
import { useReconciliationService } from "@/arches_lingo/composables/useReconciliationService.ts";

const { isServiceAvailable, serviceUrl, usageHint, copyServiceUrl } =
    useReconciliationService();

const headingId = useId();
const hintId = useId();
</script>

<template>
    <section
        v-if="isServiceAvailable"
        class="dashboard-section"
        :aria-labelledby="headingId"
    >
        <div class="section-header">
            <h2 :id="headingId">{{ $gettext("Use in OpenRefine") }}</h2>
        </div>
        <div class="url-row">
            <InputText
                class="url"
                readonly
                :model-value="serviceUrl"
                :aria-label="$gettext('Reconciliation service URL')"
                :aria-describedby="hintId"
            />
            <Button
                icon="pi pi-copy"
                :label="$gettext('Copy URL')"
                :severity="SECONDARY"
                @click="copyServiceUrl"
            />
        </div>
        <p
            :id="hintId"
            class="hint-text"
        >
            {{ usageHint }}
        </p>
    </section>
</template>

<style scoped>
.dashboard-section {
    display: flex;
    flex-direction: column;
    gap: 0.75rem;
    background: var(--p-content-background);
    padding: 0 1rem 2rem 1rem;
}

.section-header {
    border-bottom: 0.0625rem solid var(--p-highlight-focus-background);
    padding-bottom: 0.5rem;
}

.section-header h2 {
    margin: 0;
    font-size: var(--p-lingo-font-size-medium);
    font-weight: var(--p-lingo-font-weight-normal);
    color: var(--p-neutral-500);
}

.url-row {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    max-width: 48rem;
}

.url-row .url {
    flex: 1;
    min-width: 0;
    font-size: var(--p-lingo-font-size-smallnormal);
}

.hint-text {
    margin: 0;
    font-size: var(--p-lingo-font-size-small);
    color: var(--p-inputtext-placeholder-color);
}
</style>
