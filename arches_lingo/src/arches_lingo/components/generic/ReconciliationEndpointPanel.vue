<script setup lang="ts">
import { computed, useId } from "vue";

import { storeToRefs } from "pinia";
import { useGettext } from "vue3-gettext";

import Button from "primevue/button";
import InputText from "primevue/inputtext";

import { SECONDARY } from "@/arches_lingo/constants.ts";
import { useCopyToClipboard } from "@/arches_lingo/composables/useCopyToClipboard.ts";
import { useAppSettingsStore } from "@/arches_lingo/stores/useAppSettingsStore.ts";

// Scheme services are routed by Django's slug converter, so a scheme whose
// identifier is not a slug is offered the global service instead.
const SLUG_PATTERN = /^[-a-zA-Z0-9_]+$/;

const {
    schemeIdentifier,
    schemeName,
    headingLevel = 2,
} = defineProps<{
    schemeIdentifier?: string;
    schemeName?: string;
    headingLevel?: 2 | 3;
}>();

const { $gettext, interpolate } = useGettext();
const { copyToClipboard } = useCopyToClipboard();
const {
    reconciliationEnabled,
    reconciliationServiceUrl,
    schemeReconciliationServiceUrlTemplate,
} = storeToRefs(useAppSettingsStore());

const headingId = useId();
const hintId = useId();

const schemeServiceUrl = computed(() => {
    if (
        !schemeIdentifier ||
        !SLUG_PATTERN.test(schemeIdentifier) ||
        !schemeReconciliationServiceUrlTemplate.value
    ) {
        return undefined;
    }
    return schemeReconciliationServiceUrlTemplate.value.replace(
        "{scheme_identifier}",
        schemeIdentifier,
    );
});

const serviceUrl = computed(
    () => schemeServiceUrl.value ?? reconciliationServiceUrl.value,
);

const headingTag = computed(() => `h${headingLevel}`);

const usageHint = computed(() => {
    if (schemeServiceUrl.value) {
        return $gettext(
            "Add this URL as a standard reconciliation service in OpenRefine to match spreadsheet values against this scheme.",
        );
    }
    if (schemeName) {
        return interpolate(
            $gettext(
                'Add this URL as a standard reconciliation service in OpenRefine, then choose "%{scheme}" as the type to reconcile against.',
            ),
            { scheme: schemeName },
            true,
        );
    }
    return $gettext(
        "Add this URL as a standard reconciliation service in OpenRefine to match spreadsheet values against published schemes.",
    );
});

async function copyServiceUrl(): Promise<void> {
    await copyToClipboard(serviceUrl.value ?? "", {
        copiedSummary: $gettext(
            "Reconciliation service URL copied to clipboard",
        ),
        failedSummary: $gettext(
            "Unable to copy the reconciliation service URL",
        ),
    });
}
</script>

<template>
    <section
        v-if="reconciliationEnabled && serviceUrl"
        class="reconciliation-endpoint"
        :aria-labelledby="headingId"
    >
        <component
            :is="headingTag"
            :id="headingId"
            class="title"
        >
            {{ $gettext("Use in OpenRefine") }}
        </component>
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
        <span
            :id="hintId"
            class="hint"
        >
            {{ usageHint }}
        </span>
    </section>
</template>

<style scoped>
.reconciliation-endpoint {
    display: flex;
    flex-direction: column;
    gap: 0.375rem;
}

.reconciliation-endpoint .title {
    margin: 0;
    font-size: var(--p-lingo-font-size-small);
    font-weight: normal;
    color: var(--p-text-muted-color);
}

.reconciliation-endpoint .url-row {
    display: flex;
    align-items: center;
    gap: 0.5rem;
}

.reconciliation-endpoint .url-row .url {
    flex: 1;
    min-width: 0;
    font-size: var(--p-lingo-font-size-small);
}

.reconciliation-endpoint .hint {
    font-size: var(--p-lingo-font-size-small);
    color: var(--p-text-muted-color);
}
</style>
