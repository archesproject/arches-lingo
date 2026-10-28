<script setup lang="ts">
import { useId } from "vue";

import Button from "primevue/button";

defineOptions({ inheritAttrs: false });

const { isDisabled, disabledReason } = defineProps<{
    isDisabled: boolean;
    disabledReason: string;
}>();

const emit = defineEmits<{
    click: [event: MouseEvent];
}>();

const disabledReasonId = useId();

const TOOLTIP_PASS_THROUGH = {
    text: { style: { fontFamily: "var(--p-lingo-font-family)" } },
    arrow: { style: { display: "none" } },
};

function onClick(event: MouseEvent) {
    if (!isDisabled) {
        emit("click", event);
    }
}
</script>

<template>
    <span class="disabled-reason-button">
        <Button
            v-tooltip.top="{
                disabled: !isDisabled,
                value: disabledReason,
                showDelay: 300,
                pt: TOOLTIP_PASS_THROUGH,
            }"
            v-bind="$attrs"
            :class="{ 'is-disabled': isDisabled }"
            :aria-disabled="isDisabled"
            :aria-describedby="isDisabled ? disabledReasonId : undefined"
            @click="onClick"
        />
        <span
            v-if="isDisabled"
            :id="disabledReasonId"
            class="p-hidden-accessible"
        >
            {{ disabledReason }}
        </span>
    </span>
</template>

<style scoped>
/* .p-disabled would also set pointer-events: none and block the tooltip. */
.is-disabled {
    opacity: var(--p-disabled-opacity);
    cursor: default;
}
</style>
