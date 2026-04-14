<script setup lang="ts">
import { computed, inject } from "vue";
import { useGettext } from "vue3-gettext";

import Button from "primevue/button";

import GenericWidget from "@/arches_component_lab/generics/GenericWidget/GenericWidget.vue";

import { VIEW } from "@/arches_lingo/constants.ts";
import { useUserStore } from "@/arches_lingo/stores/useUserStore.ts";

import type { SchemeCreation } from "@/arches_lingo/types.ts";

const props = defineProps<{
    componentName: string;
    graphSlug: string;
    resourceInstanceId: string | undefined;
    sectionTitle: string;
    tileData: SchemeCreation | undefined;
}>();

const { $gettext } = useGettext();

const openEditor =
    inject<(componentName: string, tileId: string | undefined) => void>(
        "openEditor",
    );

const resourceInstanceLifecycleState = inject<{
    value:
        | {
              can_edit_resource_instances: boolean;
              can_delete_resource_instances: boolean;
          }
        | undefined;
}>("resourceInstanceLifecycleState");

const canEditResourceInstances = computed(() => {
    return Boolean(
        resourceInstanceLifecycleState?.value?.can_edit_resource_instances,
    );
});

const isCreateDisabled = computed(() => {
    return Boolean(
        !props.resourceInstanceId || !canEditResourceInstances.value,
    );
});

const createTooltipText = computed(() => {
    if (!isCreateDisabled.value) {
        return "";
    }

    if (!props.resourceInstanceId) {
        return $gettext("Create a Scheme Label before adding standards");
    }

    return $gettext(
        "This scheme is not editable in its current lifecycle state",
    );
});
const { isEditor } = useUserStore();

const buttonLabel = computed(() => {
    if (props.tileData) {
        return $gettext("Edit Scheme Standard");
    }
    return $gettext("Add Standard");
});

const buttonIcon = computed(() => {
    if (props.tileData) {
        return "pi pi-pencil";
    }
    return "pi pi-plus-circle";
});
</script>

<template>
    <div class="viewer-section">
        <div class="section-header">
            <h2>{{ props.sectionTitle }}</h2>

            <Button
                v-if="isEditor"
                v-tooltip.top="{
                    disabled: Boolean(!isCreateDisabled),
                    value: createTooltipText,
                    showDelay: 300,
                    pt: {
                        text: {
                            style: { fontFamily: 'var(--p-lingo-font-family)' },
                        },
                        arrow: { style: { display: 'none' } },
                    },
                }"
                :disabled="isCreateDisabled"
                :label="buttonLabel"
                :icon="buttonIcon"
                class="add-button"
                @click="
                    openEditor!(props.componentName, props.tileData?.tileid)
                "
            ></Button>
        </div>

        <div
            v-if="props.tileData"
            class="fields-container"
        >
            <GenericWidget
                node-alias="creation_sources"
                :graph-slug="props.graphSlug"
                :aliased-node-data="
                    props.tileData.aliased_data.creation_sources
                "
                :mode="VIEW"
            />
        </div>

        <div
            v-else
            class="section-message"
        >
            {{ $gettext("No Scheme Standards were found.") }}
        </div>
    </div>
</template>

<style scoped>
.fields-container {
    padding-top: 0.5rem;
    color: var(--p-inputtext-placeholder-color);
    font-size: var(--p-lingo-font-size-smallnormal);
    font-weight: var(--p-lingo-font-weight-light);
}

:deep(.widget-label) {
    font-size: var(--p-lingo-font-size-smallnormal);
    font-weight: var(--p-lingo-font-weight-normal);
    color: var(--p-neutral-400);
    margin-bottom: 0.125rem;
}

:deep(.widget > div) {
    padding-inline-start: 0.75rem;
}

:deep(.add-button .pi-pencil) {
    font-size: 0.7rem;
}
</style>
