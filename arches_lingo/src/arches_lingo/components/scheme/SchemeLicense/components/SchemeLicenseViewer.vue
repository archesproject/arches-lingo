<script setup lang="ts">
import { computed, inject } from "vue";
import { useGettext } from "vue3-gettext";

import Button from "primevue/button";

import GenericWidget from "@/arches_component_lab/generics/GenericWidget/GenericWidget.vue";

import { VIEW } from "@/arches_lingo/constants.ts";
import { useUserStore } from "@/arches_lingo/stores/useUserStore.ts";

import type { SchemeRights } from "@/arches_lingo/types";

const props = defineProps<{
    componentName: string;
    graphSlug: string;
    resourceInstanceId: string | undefined;
    sectionTitle: string;
    tileData: SchemeRights | undefined;
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
        return $gettext("Create a Scheme Label before adding rights");
    }

    return $gettext(
        "This scheme is not editable in its current lifecycle state",
    );
});
const { isEditor } = useUserStore();

const buttonLabel = computed(() => {
    if (props.tileData) {
        return $gettext("Edit Rights");
    }
    return $gettext("Add Rights");
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
                size="small"
                @click="
                    openEditor!(props.componentName, props.tileData?.tileid)
                "
            ></Button>
        </div>

        <div
            v-if="props.tileData"
            class="fields-container"
        >
            <div class="primary-fields">
                <GenericWidget
                    node-alias="right_holder"
                    :graph-slug="props.graphSlug"
                    :aliased-node-data="
                        props.tileData?.aliased_data.right_holder
                    "
                    :mode="VIEW"
                />
                <GenericWidget
                    node-alias="right_type"
                    :graph-slug="props.graphSlug"
                    :aliased-node-data="props.tileData?.aliased_data.right_type"
                    :mode="VIEW"
                />
            </div>
            <div
                v-if="props.tileData?.aliased_data.right_statement"
                class="statement-section"
            >
                <span class="group-label">{{
                    $gettext("Rights Statement")
                }}</span>
                <div class="right-statement-group">
                    <GenericWidget
                        node-alias="right_statement_content"
                        :graph-slug="props.graphSlug"
                        :aliased-node-data="
                            props.tileData?.aliased_data.right_statement
                                ?.aliased_data?.right_statement_content
                        "
                        :mode="VIEW"
                    />
                    <GenericWidget
                        node-alias="right_statement_language"
                        :graph-slug="props.graphSlug"
                        :aliased-node-data="
                            props.tileData?.aliased_data.right_statement
                                ?.aliased_data.right_statement_language
                        "
                        :mode="VIEW"
                    />
                    <GenericWidget
                        node-alias="right_statement_type"
                        :graph-slug="props.graphSlug"
                        :aliased-node-data="
                            props.tileData?.aliased_data.right_statement
                                ?.aliased_data.right_statement_type
                        "
                        :mode="VIEW"
                    />
                </div>
            </div>
        </div>
        <div
            v-else
            class="section-message"
        >
            {{ $gettext("No Scheme Rights were found.") }}
        </div>
    </div>
</template>

<style scoped>
.fields-container {
    display: flex;
    flex-direction: row;
    flex-wrap: wrap;
    align-items: flex-start;
    gap: 1.25rem;
    padding-top: 0.5rem;
    color: var(--p-inputtext-placeholder-color);
    font-size: var(--p-lingo-font-size-smallnormal);
    font-weight: var(--p-lingo-font-weight-light);
}

.primary-fields {
    display: flex;
    flex-direction: column;
    gap: 1rem;
    flex: 1;
    min-width: 14rem;
}

.statement-section {
    flex: 1;
    min-width: 16rem;
}

.group-label {
    display: block;
    font-size: var(--p-lingo-font-size-smallnormal);
    font-weight: var(--p-lingo-font-weight-normal);
    color: var(--p-neutral-400);
    margin-bottom: 0.5rem;
}

.right-statement-group {
    display: flex;
    flex-direction: column;
    gap: 0.75rem;
    border-inline-start: 0.125rem solid var(--p-highlight-focus-background);
    padding-inline-start: 1.25rem;
}

:deep(.widget-label) {
    font-size: var(--p-lingo-font-size-smallnormal);
    font-weight: var(--p-lingo-font-weight-normal);
    color: var(--p-neutral-400);
    margin-bottom: 0.125rem;
}

:deep(.widget > div),
:deep(.widget > span) {
    padding-inline-start: 1rem;
}

:deep(.add-button .pi-pencil) {
    font-size: 0.7rem;
}
</style>
