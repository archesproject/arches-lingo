<script setup lang="ts">
import { inject, nextTick, ref, computed, watch } from "vue";
import { useGettext } from "vue3-gettext";

import Button from "primevue/button";
import ConfirmDialog from "primevue/confirmdialog";
import Image from "primevue/image";
import Message from "primevue/message";
import Skeleton from "primevue/skeleton";
import Tag from "primevue/tag";
import { useConfirm } from "primevue/useconfirm";
import { useToast } from "primevue/usetoast";

import GenericWidget from "@/arches_vue_components/generics/GenericWidget/GenericWidget.vue";

import {
    DANGER,
    DEFAULT_ERROR_TOAST_LIFE,
    ERROR,
    SECONDARY,
    VIEW,
} from "@/arches_lingo/constants.ts";
import { focusWithoutScrolling } from "@/arches_lingo/utils.ts";
import { useConceptImagesEditorStore } from "@/arches_lingo/stores/useConceptImagesEditorStore.ts";
import { storeToRefs } from "pinia";
import {
    getDigitalObjectImageAlt,
    getDigitalObjectImageTitle,
    getDigitalObjectImageUrl,
} from "@/arches_lingo/components/concept/ConceptImages/components/utils.ts";
import { useLanguageStore } from "@/arches_lingo/stores/useLanguageStore.ts";
import { useUserStore } from "@/arches_lingo/stores/useUserStore.ts";

import type {
    ConceptImages,
    ConceptInstance,
    DigitalObjectInstance,
} from "@/arches_lingo/types.ts";
import {
    fetchLingoResourcePartial,
    fetchLingoResourcesBatch,
    updateLingoResource,
} from "@/arches_lingo/api.ts";

const props = defineProps<{
    componentName: string;
    graphSlug: string;
    nodegroupAlias: string;
    resourceInstanceId: string | undefined;
    sectionTitle: string;
    tileData: ConceptImages | undefined;
}>();

const openEditor =
    inject<(componentName: string, tileId?: string) => void>("openEditor");

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
        return $gettext("Create a Concept Label before adding images");
    }

    return $gettext(
        "This concept is not editable in its current lifecycle state",
    );
});
const { isEditor } = useUserStore();
const { targetDigitalObjectResourceInstanceId } = storeToRefs(
    useConceptImagesEditorStore(),
);

const { selectedLanguage } = storeToRefs(useLanguageStore());

const configurationError = ref();
const isLoading = ref(true);
const resources = ref<DigitalObjectInstance[]>();
const { $gettext } = useGettext();
const confirm = useConfirm();
const toast = useToast();
const sectionHeadingRef = ref<HTMLElement | null>(null);

// The report refreshes its resource in place after a merge rather than
// remounting this section, so the images are refetched whenever the tile does.
watch(
    () => props.tileData,
    async (tileData) => {
        const digitalObjectIds =
            tileData?.aliased_data.depicting_digital_asset_internal?.node_value
                ?.map((reference) => reference.resourceId)
                .filter(Boolean) ?? [];

        configurationError.value = undefined;
        resources.value = [];
        try {
            if (digitalObjectIds.length) {
                resources.value = await fetchLingoResourcesBatch(
                    "digital_object_system",
                    digitalObjectIds,
                );
            }
        } catch (error) {
            configurationError.value = error;
        }
        isLoading.value = false;
    },
    { immediate: true },
);

function confirmDelete(removedResourceInstanceId: string) {
    confirm.require({
        header: $gettext("Confirmation"),
        message: $gettext(
            "Do you want to remove this digital resource from concept images? (This does not delete the digital resource)",
        ),
        accept: () => removeDigitalResource(removedResourceInstanceId),
        rejectProps: {
            label: $gettext("Cancel"),
            severity: SECONDARY,
            outlined: true,
        },
        acceptProps: {
            label: $gettext("Remove"),
            severity: DANGER,
        },
    });
}

async function removeDigitalResource(removedResourceInstanceId: string) {
    const resourceInstanceId = props.tileData?.resourceinstance;
    if (!resourceInstanceId) {
        return;
    }

    isLoading.value = true;
    try {
        const resource: ConceptInstance = await fetchLingoResourcePartial(
            props.graphSlug,
            resourceInstanceId,
            props.nodegroupAlias,
        );

        const depictingDigitalAssetInternalData =
            resource.aliased_data.depicting_digital_asset_internal
                ?.aliased_data;
        if (
            depictingDigitalAssetInternalData?.depicting_digital_asset_internal
        ) {
            const currentNodeValue =
                depictingDigitalAssetInternalData
                    .depicting_digital_asset_internal.node_value ?? [];
            depictingDigitalAssetInternalData.depicting_digital_asset_internal.node_value =
                currentNodeValue.filter(
                    (ref) => ref.resourceId !== removedResourceInstanceId,
                );
            await updateLingoResource(
                props.graphSlug,
                resourceInstanceId,
                resource,
            );
            resources.value = resources.value?.filter(
                (resource) =>
                    resource.resourceinstanceid !== removedResourceInstanceId,
            );
        }
        newResource();
    } catch (error) {
        toast.add({
            severity: ERROR,
            life: DEFAULT_ERROR_TOAST_LIFE,
            summary: $gettext("Failed to remove the image."),
            detail: error instanceof Error ? error.message : undefined,
        });
    } finally {
        isLoading.value = false;
    }

    await nextTick();
    if (sectionHeadingRef.value) {
        focusWithoutScrolling(sectionHeadingRef.value);
    }
}

function getImageName(resource: DigitalObjectInstance): string {
    return (
        getDigitalObjectImageTitle(resource, selectedLanguage.value.code) ||
        $gettext("image")
    );
}

function newResource() {
    modifyResource();
}

function editResource(resourceInstanceId: string) {
    modifyResource(resourceInstanceId);
}

function modifyResource(resourceInstanceId?: string) {
    targetDigitalObjectResourceInstanceId.value = resourceInstanceId;
    openEditor!(props.componentName);
}
</script>

<template>
    <div class="viewer-section">
        <ConfirmDialog />

        <div class="section-header">
            <div class="section-title">
                <h2 ref="sectionHeadingRef">{{ props.sectionTitle }}</h2>
                <Tag
                    v-if="resources?.length"
                    :value="String(resources.length)"
                    severity="secondary"
                />
            </div>
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
                :label="$gettext('Add Image')"
                class="add-button"
                icon="pi pi-plus-circle"
                @click="newResource"
            ></Button>
        </div>

        <Skeleton
            v-if="isLoading"
            style="width: 100%"
        />

        <Message
            v-else-if="configurationError"
            severity="error"
            size="small"
        >
            {{ configurationError.message }}
        </Message>

        <div
            v-else-if="!resources || !resources.length"
            class="section-message"
        >
            {{ $gettext("No concept images were found.") }}
        </div>

        <div
            v-else
            class="concept-images-scroll"
        >
            <div class="concept-images">
                <div
                    v-for="resource in resources"
                    :key="resource.resourceinstanceid"
                    class="concept-image-card"
                >
                    <div class="image-container">
                        <Image
                            v-if="getDigitalObjectImageUrl(resource)"
                            :src="getDigitalObjectImageUrl(resource)"
                            :alt="
                                getDigitalObjectImageAlt(
                                    resource,
                                    selectedLanguage.code,
                                )
                            "
                            preview
                            class="card-image"
                        />
                        <div
                            v-else
                            class="image-placeholder"
                        >
                            <i
                                class="pi pi-image"
                                aria-hidden="true"
                            />
                        </div>
                    </div>
                    <div class="card-body">
                        <div class="card-header">
                            <span class="image-title">
                                <GenericWidget
                                    node-alias="name_content"
                                    graph-slug="digital_object_system"
                                    :mode="VIEW"
                                    :aliased-node-data="
                                        resource.aliased_data.name?.aliased_data
                                            .name_content
                                    "
                                    :should-show-label="false"
                                />
                            </span>
                            <div
                                v-if="isEditor"
                                class="button-container"
                            >
                                <Button
                                    v-if="canEditResourceInstances"
                                    class="controls edit-button"
                                    icon="pi pi-file-edit"
                                    variant="text"
                                    :aria-label="
                                        $gettext(
                                            'Edit %{imageName}',
                                            {
                                                imageName:
                                                    getImageName(resource),
                                            },
                                            true,
                                        )
                                    "
                                    @click="
                                        editResource(
                                            resource.resourceinstanceid,
                                        )
                                    "
                                />
                                <Button
                                    v-if="canEditResourceInstances"
                                    class="controls delete-button"
                                    icon="pi pi-trash"
                                    :aria-label="
                                        $gettext(
                                            'Remove %{imageName}',
                                            {
                                                imageName:
                                                    getImageName(resource),
                                            },
                                            true,
                                        )
                                    "
                                    variant="text"
                                    @click="
                                        confirmDelete(
                                            resource.resourceinstanceid,
                                        )
                                    "
                                />
                            </div>
                        </div>
                        <div
                            v-if="
                                resource.aliased_data.statement?.aliased_data
                                    .statement_content ?? null
                            "
                            class="card-description"
                        >
                            <GenericWidget
                                node-alias="statement_content"
                                graph-slug="digital_object_system"
                                :mode="VIEW"
                                :aliased-node-data="
                                    resource.aliased_data.statement
                                        ?.aliased_data.statement_content
                                "
                                :should-show-label="false"
                            />
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </div>
</template>

<style scoped>
.concept-images-scroll {
    overflow-x: auto;
    overflow-y: hidden;
    padding: 0.75rem 0;
}

.concept-images {
    display: flex;
    gap: 1rem;
    width: fit-content;
}

.concept-image-card {
    width: 20rem;
    border-radius: 0.25rem;
    border: 0.0625rem solid var(--p-content-border-color);
    background: var(--p-content-background);
    overflow: hidden;
    display: flex;
    flex-direction: column;
}

.image-container {
    display: flex;
    align-items: center;
    justify-content: center;
    background: var(--p-surface-100);
    overflow: hidden;
    min-height: 12rem;
    max-height: 16rem;
}

.image-container :deep(.card-image img) {
    max-height: 16rem;
    width: 100%;
    object-fit: contain;
    display: block;
    cursor: pointer;
}

.image-container :deep(.card-image) {
    width: 100%;
    height: 100%;
    display: flex;
}

.image-placeholder {
    display: flex;
    align-items: center;
    justify-content: center;
    width: 100%;
    min-height: 12rem;
    color: var(--p-text-muted-color);
    font-size: 2rem;
}

.card-body {
    display: flex;
    flex-direction: column;
    gap: 0.5rem;
    padding: 0.75rem;
}

.card-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 0.5rem;
}

.image-title {
    font-size: var(--p-lingo-font-size-smallnormal);
    font-weight: var(--p-lingo-font-weight-normal);
    color: var(--p-text-color);
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
    flex: 1;
    min-width: 0;
}

.card-description {
    font-size: var(--p-lingo-font-size-xsmall);
    color: var(--p-inputtext-placeholder-color);
    line-height: 1.4;
}

.button-container {
    display: flex;
    gap: 0.25rem;
    flex-shrink: 0;
}

.controls {
    width: 2rem;
    height: 2rem;
    border-radius: 50%;
    padding: 1.2rem;
    color: var(--p-button-primary-color);
}

.edit-button {
    background: var(--p-button-primary-background);
    border: 0.0625rem solid var(--p-button-primary-active-border-color);
}

.delete-button {
    background: var(--p-button-danger-background);
    border: 0.0625rem solid var(--p-button-danger-border-color);
    color: var(--p-button-danger-color);
}

.button-container .edit-button:hover {
    background: var(--p-button-primary-hover-background);
    border: 0.0625rem solid var(--p-button-primary-hover-border-color);
    color: var(--p-button-primary-hover-color);
}

.button-container .delete-button:hover {
    background: var(--p-button-danger-hover-background);
    border: 0.0625rem solid var(--p-button-danger-hover-border-color);
    color: var(--p-button-danger-hover-color);
}
</style>
