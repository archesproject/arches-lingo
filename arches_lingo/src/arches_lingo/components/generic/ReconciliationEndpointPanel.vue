<script setup lang="ts">
import { computed } from "vue";

import { storeToRefs } from "pinia";
import { useGettext } from "vue3-gettext";
import { useToast } from "primevue/usetoast";

import Button from "primevue/button";
import InputText from "primevue/inputtext";

import { generateArchesURL } from "@/arches/utils/generate-arches-url.ts";
import {
    DEFAULT_ERROR_TOAST_LIFE,
    DEFAULT_TOAST_LIFE,
    ERROR,
    SECONDARY,
    SUCCESS,
} from "@/arches_lingo/constants.ts";
import { useAppSettingsStore } from "@/arches_lingo/stores/useAppSettingsStore.ts";

const { schemeIdentifier, schemeName } = defineProps<{
    schemeIdentifier?: string;
    schemeName?: string;
}>();

const { $gettext } = useGettext();
const toast = useToast();
const { publicServerAddress, reconciliationEnabled, reconciliationServiceUrl } =
    storeToRefs(useAppSettingsStore());

const serviceUrl = computed(() => {
    if (!schemeIdentifier || !publicServerAddress.value) {
        return reconciliationServiceUrl.value;
    }
    const schemeServicePath = generateArchesURL(
        "arches_lingo:api-lingo-scheme-reconcile",
        { scheme_identifier: schemeIdentifier },
    );
    return `${publicServerAddress.value.replace(/\/+$/, "")}${schemeServicePath}`;
});

const usageHint = computed(() => {
    if (schemeIdentifier) {
        return $gettext(
            "Add this URL as a standard reconciliation service in OpenRefine to match spreadsheet values against this scheme.",
        );
    }
    if (schemeName) {
        return $gettext(
            'Add this URL as a standard reconciliation service in OpenRefine, then choose "%{scheme}" as the type to reconcile against.',
            { scheme: schemeName },
        );
    }
    return $gettext(
        "Add this URL as a standard reconciliation service in OpenRefine to match spreadsheet values against published schemes.",
    );
});

async function copyServiceUrl(): Promise<void> {
    try {
        await navigator.clipboard.writeText(serviceUrl.value ?? "");
        toast.add({
            severity: SUCCESS,
            life: DEFAULT_TOAST_LIFE,
            summary: $gettext("Reconciliation service URL copied to clipboard"),
        });
    } catch (error) {
        toast.add({
            severity: ERROR,
            life: DEFAULT_ERROR_TOAST_LIFE,
            summary: $gettext("Unable to copy the reconciliation service URL"),
            detail: error instanceof Error ? error.message : undefined,
        });
    }
}
</script>

<template>
    <section
        v-if="reconciliationEnabled && serviceUrl"
        class="reconciliation-endpoint"
        :aria-label="$gettext('OpenRefine reconciliation service')"
    >
        <span class="title">{{ $gettext("Use in OpenRefine") }}</span>
        <div class="url-row">
            <InputText
                class="url"
                readonly
                :model-value="serviceUrl"
                :aria-label="$gettext('Reconciliation service URL')"
            />
            <Button
                icon="pi pi-copy"
                :label="$gettext('Copy')"
                :severity="SECONDARY"
                @click="copyServiceUrl"
            />
        </div>
        <span class="hint">{{ usageHint }}</span>
    </section>
</template>

<style scoped>
.reconciliation-endpoint {
    display: flex;
    flex-direction: column;
    gap: 0.375rem;
}

.reconciliation-endpoint .title {
    font-size: var(--p-lingo-font-size-small);
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
