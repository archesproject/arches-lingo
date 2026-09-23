<script setup lang="ts">
import { useGettext } from "vue3-gettext";
import Image from "primevue/image";

import {
    getDigitalObjectImageAlt,
    getDigitalObjectImageUrl,
} from "@/arches_lingo/components/concept/ConceptImages/components/utils.ts";

import type { DigitalObjectInstance } from "@/arches_lingo/types.ts";

const { digitalObjectIds, digitalObjectsById } = defineProps<{
    digitalObjectIds: string[];
    digitalObjectsById: Map<string, DigitalObjectInstance>;
}>();

const { $gettext } = useGettext();

function getImageUrl(digitalObjectId: string) {
    const digitalObject = digitalObjectsById.get(digitalObjectId);
    return digitalObject ? getDigitalObjectImageUrl(digitalObject) : undefined;
}

function getImageAlt(digitalObjectId: string) {
    const digitalObject = digitalObjectsById.get(digitalObjectId);
    return digitalObject ? getDigitalObjectImageAlt(digitalObject) : "";
}

function getImageName(digitalObjectId: string) {
    return (
        digitalObjectsById.get(digitalObjectId)?.aliased_data.name?.aliased_data
            .name_content?.display_value || $gettext("Untitled")
    );
}

function getImageDescription(digitalObjectId: string) {
    return (
        digitalObjectsById.get(digitalObjectId)?.aliased_data.statement
            ?.aliased_data.statement_content?.display_value ?? ""
    );
}
</script>

<template>
    <ul class="merge-digital-objects">
        <li
            v-for="digitalObjectId in digitalObjectIds"
            :key="digitalObjectId"
            class="merge-digital-object"
        >
            <div class="merge-digital-object-thumbnail">
                <Image
                    v-if="getImageUrl(digitalObjectId)"
                    :src="getImageUrl(digitalObjectId)"
                    :alt="getImageAlt(digitalObjectId)"
                    preview
                />
                <i
                    v-else
                    class="pi pi-image"
                    aria-hidden="true"
                />
            </div>
            <div class="merge-digital-object-text">
                <span class="merge-digital-object-name">
                    {{ getImageName(digitalObjectId) }}
                </span>
                <span
                    v-if="getImageDescription(digitalObjectId)"
                    class="merge-digital-object-description"
                >
                    {{ getImageDescription(digitalObjectId) }}
                </span>
            </div>
        </li>
    </ul>
</template>

<style scoped>
.merge-digital-objects {
    display: flex;
    flex-direction: column;
    gap: 0.5rem;
    margin: 0;
    padding: 0;
    list-style: none;
}

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

/* The same size and colour the tile card gives its secondary values. */
.merge-digital-object-description {
    font-size: var(--p-lingo-font-size-smallnormal);
    color: var(--p-inputtext-placeholder-color);
    overflow-wrap: anywhere;
}
</style>
