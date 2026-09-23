<script setup lang="ts">
import { computed } from "vue";

import { useGettext } from "vue3-gettext";
import Image from "primevue/image";

import MergeCard from "@/arches_lingo/components/concept/ConceptMerge/components/MergeCard.vue";

import {
    getDigitalObjectImageAlt,
    getDigitalObjectImageUrl,
} from "@/arches_lingo/components/concept/ConceptImages/components/utils.ts";

import type { DigitalObjectInstance } from "@/arches_lingo/types.ts";

const { digitalObject, alreadyOnSurvivor } = defineProps<{
    // Undefined until the digital objects arrive, or if fetching them failed.
    digitalObject: DigitalObjectInstance | undefined;
    alreadyOnSurvivor?: boolean;
}>();

const { $gettext } = useGettext();

const imageUrl = computed(function () {
    return digitalObject ? getDigitalObjectImageUrl(digitalObject) : undefined;
});

const imageAlt = computed(function () {
    return digitalObject ? getDigitalObjectImageAlt(digitalObject) : "";
});

const imageName = computed(function () {
    return (
        digitalObject?.aliased_data.name?.aliased_data.name_content
            ?.display_value || $gettext("Untitled")
    );
});

const imageDescription = computed(function () {
    return (
        digitalObject?.aliased_data.statement?.aliased_data.statement_content
            ?.display_value ?? ""
    );
});
</script>

<template>
    <MergeCard :already-on-survivor="alreadyOnSurvivor">
        <template #control>
            <slot name="control" />
        </template>
        <div class="merge-digital-object">
            <div class="merge-digital-object-thumbnail">
                <Image
                    v-if="imageUrl"
                    :src="imageUrl"
                    :alt="imageAlt"
                    preview
                />
                <i
                    v-else
                    class="pi pi-image"
                    aria-hidden="true"
                />
            </div>
            <div class="merge-digital-object-text">
                <span class="merge-digital-object-name">{{ imageName }}</span>
                <span
                    v-if="imageDescription"
                    class="merge-digital-object-description"
                >
                    {{ imageDescription }}
                </span>
            </div>
        </div>
    </MergeCard>
</template>

<style scoped>
.merge-digital-object {
    display: flex;
    align-items: flex-start;
    gap: 0.625rem;
    min-width: 0;
}

.merge-digital-object-thumbnail {
    display: flex;
    flex-shrink: 0;
    align-items: center;
    justify-content: center;
    width: 4rem;
    height: 4rem;
    overflow: hidden;
    border-radius: 0.125rem;
    background: var(--p-surface-100);
    color: var(--p-text-muted-color);
    font-size: 1.5rem;
}

.merge-digital-object-thumbnail :deep(.p-image),
.merge-digital-object-thumbnail :deep(img) {
    display: block;
    width: 100%;
    height: 100%;
    object-fit: cover;
    cursor: pointer;
}

.merge-digital-object-text {
    display: flex;
    flex-direction: column;
    gap: 0.125rem;
    min-width: 0;
}

.merge-digital-object-name {
    font-size: var(--p-lingo-font-size-smallnormal);
    color: var(--p-text-color);
    overflow-wrap: anywhere;
}

/* The same size and colour a tile card gives its secondary values. */
.merge-digital-object-description {
    font-size: var(--p-lingo-font-size-smallnormal);
    color: var(--p-inputtext-placeholder-color);
    overflow-wrap: anywhere;
}
</style>
