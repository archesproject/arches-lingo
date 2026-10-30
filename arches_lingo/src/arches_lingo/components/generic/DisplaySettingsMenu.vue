<script setup lang="ts">
import { ref, useTemplateRef } from "vue";
import { useGettext } from "vue3-gettext";

import Button from "primevue/button";
import Popover from "primevue/popover";

import ThemeSelector from "@/arches_lingo/components/header/PageHeader/components/UserInteraction/components/UserInteractionMenu/components/ThemeSelector.vue";
import { focusFirstFocusableElement } from "@/arches_lingo/utils.ts";

import type { PopoverMethods } from "primevue/popover";

const { $gettext } = useGettext();

const popover = useTemplateRef<PopoverMethods>("popover");
const settingsPanel = useTemplateRef<HTMLElement>("settingsPanel");
const isPopoverVisible = ref(false);

function togglePopover(event: MouseEvent) {
    popover.value!.toggle(event);
}

function onPopoverShow() {
    isPopoverVisible.value = true;
    focusFirstFocusableElement(settingsPanel.value);
}
</script>

<template>
    <div class="display-settings-menu">
        <Button
            icon="pi pi-palette"
            severity="secondary"
            outlined
            :label="$gettext('Display')"
            aria-haspopup="dialog"
            :aria-expanded="isPopoverVisible"
            @click="togglePopover"
        />

        <Popover
            ref="popover"
            :aria-label="$gettext('Display settings')"
            @show="onPopoverShow"
            @hide="isPopoverVisible = false"
        >
            <div
                ref="settingsPanel"
                class="display-settings-panel"
            >
                <ThemeSelector />
            </div>
        </Popover>
    </div>
</template>

<style scoped>
.display-settings-panel {
    font-family: var(--p-lingo-font-family);
    width: 16rem;
}
</style>
