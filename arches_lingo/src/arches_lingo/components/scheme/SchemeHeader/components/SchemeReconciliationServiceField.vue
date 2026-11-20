<script setup lang="ts">
import { useId, useTemplateRef } from "vue";

import Button from "primevue/button";
import Popover from "primevue/popover";

import { useReconciliationService } from "@/arches_lingo/composables/useReconciliationService.ts";

import type { PopoverMethods } from "primevue/popover";

const { schemeIdentifier, schemeName } = defineProps<{
    schemeIdentifier: string | undefined;
    schemeName: string | undefined;
}>();

const { serviceUrl, usageHint, copyServiceUrl } = useReconciliationService(
    () => schemeIdentifier,
    () => schemeName,
);

const usageHintId = useId();
const usageHintPopover = useTemplateRef<PopoverMethods>("usageHintPopover");

function toggleUsageHint(event: MouseEvent): void {
    usageHintPopover.value!.toggle(event);
}
</script>

<template>
    <div class="header-item">
        <span class="header-item-label">
            {{ $gettext("OpenRefine service:") }}
        </span>
        <Button
            class="usage-hint-toggle"
            icon="pi pi-info-circle"
            variant="text"
            size="small"
            :rounded="true"
            :aria-label="$gettext('How to use the OpenRefine service')"
            :aria-describedby="usageHintId"
            @click="toggleUsageHint"
        />
        <span class="header-item-value">{{ serviceUrl }}</span>
        <Button
            icon="pi pi-copy"
            class="copy-button"
            variant="link"
            :aria-label="$gettext('Copy OpenRefine service URL')"
            @click="copyServiceUrl"
        />
        <span
            :id="usageHintId"
            hidden
        >
            {{ usageHint }}
        </span>
        <!-- Screen readers get the hint through aria-describedby on the toggle,
             so the visual copy is hidden from them. -->
        <Popover
            ref="usageHintPopover"
            :pt="{ root: { 'aria-hidden': 'true' } }"
        >
            <p class="usage-hint">{{ usageHint }}</p>
        </Popover>
    </div>
</template>

<style scoped>
.usage-hint-toggle {
    flex-shrink: 0;
    color: var(--p-header-item-label);
}

.copy-button {
    flex-shrink: 0;
    min-inline-size: 1.5rem;
    min-block-size: 1.5rem;
    padding: 0;
    margin: 0;
    font-size: var(--p-lingo-font-size-small);
    color: var(--p-primary-500);
}

.usage-hint {
    margin: 0;
    max-inline-size: 24rem;
    font-size: var(--p-lingo-font-size-small);
}
</style>
