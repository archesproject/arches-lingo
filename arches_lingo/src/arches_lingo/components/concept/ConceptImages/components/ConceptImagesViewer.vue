<script setup lang="ts">
import { inject, ref, onMounted, nextTick } from "vue";
import { useGettext } from "vue3-gettext";

import Button from "primevue/button";
import ConfirmDialog from "primevue/confirmdialog";
import Message from "primevue/message";
import ProgressSpinner from "primevue/progressspinner";
import { useConfirm } from "primevue/useconfirm";

import FileListWidget from "@/arches_component_lab/widgets/FileListWidget/FileListWidget.vue";
import NonLocalizedStringWidget from "@/arches_component_lab/widgets/NonLocalizedStringWidget/NonLocalizedStringWidget.vue";
import NonLocalizedTextAreaWidget from "@/arches_component_lab/widgets/NonLocalizedTextAreaWidget/NonLocalizedTextAreaWidget.vue";

import { DANGER, SECONDARY, VIEW } from "@/arches_lingo/constants.ts";

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
    tileData: ConceptImages | undefined;
    componentName: string;
    sectionTitle: string;
    graphSlug: string;
    nodegroupAlias: string;
}>();

const openEditor =
    inject<(componentName: string, tileId?: string) => void>("openEditor");
const updateAfterComponentDeletion = inject<
    (componentName: string, tileId: string) => void
>("updateAfterComponentDeletion");

const configurationError = ref();
const isLoading = ref(true);
const resources = ref<DigitalObjectInstance[]>();
const { $gettext } = useGettext();
const confirm = useConfirm();

onMounted(async () => {
    if (props.tileData) {
        try {
            const digitalObjectInstances =
                props.tileData.aliased_data.depicting_digital_asset_internal?.interchange_value?.map(
                    (resource) => resource.resource_id,
                );
            if (digitalObjectInstances) {
                resources.value = await fetchLingoResourcesBatch(
                    "digital_object_rdm_system",
                    digitalObjectInstances,
                );
            }
        } catch (error) {
            configurationError.value = error;
        }
    }
    isLoading.value = false;
});

function confirmDelete(removedResourceInstanceId: string) {
    confirm.require({
        header: $gettext("Confirmation"),
        message: $gettext(
            "Do you want to remove this digital resource from concept images? (This does not delete the digital resource)",
        ),
        accept: async () => {
            const resourceInstanceId = props.tileData?.resourceinstance;
            if (resourceInstanceId) {
                const resource: ConceptInstance =
                    await fetchLingoResourcePartial(
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
                    depictingDigitalAssetInternalData.depicting_digital_asset_internal.interchange_value =
                        depictingDigitalAssetInternalData.depicting_digital_asset_internal.interchange_value.filter(
                            (assetReference) =>
                                assetReference.resource_id !==
                                removedResourceInstanceId,
                        );
                    resources.value = resources.value?.filter(
                        (resource) =>
                            resource.resourceinstanceid !==
                            removedResourceInstanceId,
                    );
                    await updateLingoResource(
                        props.graphSlug,
                        resourceInstanceId,
                        resource,
                    );

                    updateAfterComponentDeletion!(
                        props.componentName,
                        props.tileData.tileid!,
                    );
                }
            }
        },
        rejectProps: {
            label: $gettext("Cancel"),
            severity: SECONDARY,
            outlined: true,
        },
        acceptProps: {
            label: $gettext("Delete"),
            severity: DANGER,
        },
    });
}

function newResource() {
    modifyResource();
}

function editResource(resourceInstanceId: string) {
    modifyResource(resourceInstanceId);
}

function modifyResource(resourceInstanceId?: string) {
    openEditor!(props.componentName);

    nextTick(() => {
        const openConceptImagesEditor = new CustomEvent(
            "openConceptImagesEditor",
            { detail: { resourceInstanceId: resourceInstanceId } },
        );
        document.dispatchEvent(openConceptImagesEditor);
    });
}
</script>

<template>
    <div class="viewer-section">
        <ConfirmDialog />

        <div class="section-header">
            <h2>{{ props.sectionTitle }}</h2>
            <Button
                :label="$gettext('Add Image')"
                class="add-button"
                @click="newResource"
            ></Button>
        </div>

        <ProgressSpinner
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
            style="overflow-x: auto"
        >
            <div class="concept-images">
                <div
                    v-for="resource in resources"
                    :key="resource.resourceinstanceid"
                    class="concept-image"
                >
                    <div class="header">
                        <label
                            for="concept-image"
                            class="text"
                        >
                            <NonLocalizedStringWidget
                                node-alias="name_content"
                                graph-slug="digital_object_rdm_system"
                                :mode="VIEW"
                                :initial-value="
                                    resource.aliased_data.name?.aliased_data
                                        .name_content?.display_value
                                "
                            />
                        </label>
                        <div class="buttons">
                            <Button
                                icon="pi pi-file-edit"
                                rounded
                                @click="
                                    editResource(resource.resourceinstanceid)
                                "
                            />
                            <Button
                                icon="pi pi-trash"
                                :aria-label="$gettext('Delete')"
                                severity="danger"
                                rounded
                                @click="
                                    confirmDelete(resource.resourceinstanceid)
                                "
                            />
                        </div>
                    </div>
                    <FileListWidget
                        node-alias="content"
                        graph-slug="digital_object_rdm_system"
                        :initial-value="
                            resource.aliased_data.content?.aliased_data.content
                                ?.interchange_value
                        "
                        :mode="VIEW"
                        :show-label="false"
                    />
                    <div class="footer">
                        <NonLocalizedTextAreaWidget
                            node-alias="statement_content"
                            graph-slug="digital_object_rdm_system"
                            :mode="VIEW"
                            :initial-value="
                                resource.aliased_data.statement?.aliased_data
                                    .statement_content?.display_value
                            "
                        />
                    </div>
                </div>
            </div>
        </div>
    </div>
</template>

<style scoped>
.buttons {
    display: flex;
    justify-content: center;
    gap: 1rem;
}

.concept-images {
    display: flex;
    flex-direction: row;
    align-items: start;
    width: fit-content;
    color: var(--p-inputtext-placeholder-color);
    font-size: var(--p-lingo-font-size-smallnormal);
}

.concept-image {
    width: 30rem;
    margin: 0 1rem;
}

.concept-image .header {
    display: grid;
    grid-template-columns: 1fr auto;
    padding: 1rem 0;
}

.concept-image .footer {
    padding-top: 1rem;
}

.concept-image .header .text {
    display: flex;
    align-items: start;
    flex-direction: column;
}

.concept-images :deep(.p-galleria) {
    border: none;
}
</style>
