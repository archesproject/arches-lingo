<script setup lang="ts">
import { useGettext } from "vue3-gettext";
import Tag from "primevue/tag";

const { alreadyOnSurvivor } = defineProps<{
    alreadyOnSurvivor?: boolean;
}>();

const { $gettext } = useGettext();
</script>

<template>
    <div
        class="merge-card"
        :class="{ muted: alreadyOnSurvivor }"
    >
        <div class="merge-card-control">
            <slot name="control" />
        </div>
        <div class="merge-card-body">
            <slot />
            <Tag
                v-if="alreadyOnSurvivor"
                class="merge-card-tag"
                severity="secondary"
                :value="$gettext('Already present')"
            />
        </div>
    </div>
</template>

<style scoped>
.merge-card {
    display: flex;
    align-items: flex-start;
    gap: 0.5rem;
    padding: 0.5rem 0.625rem;
    border: 0.0625rem solid var(--p-content-border-color);
    border-radius: 0.125rem;
    background: var(--p-content-background);
}

.merge-card.muted {
    opacity: 0.6;
}

.merge-card-control {
    display: flex;
    align-items: center;
    min-height: 1.5rem;
}

.merge-card-body {
    display: flex;
    flex-direction: column;
    gap: 0.125rem;
    min-width: 0;
}

.merge-card-tag {
    align-self: flex-start;
    margin-top: 0.25rem;
    font-size: var(--p-lingo-font-size-xxsmall);
}
</style>
