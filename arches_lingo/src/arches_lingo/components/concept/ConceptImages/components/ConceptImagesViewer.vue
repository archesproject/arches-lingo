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

const configurationError = ref();
const isLoading = ref(true);
const resources = ref<DigitalObjectInstance[]>();
const { $gettext } = useGettext();
const confirm = useConfirm();

onMounted(async () => {
    if (props.tileData) {
        try {
            const digitalObjectInstances =
                props.tileData.aliased_data.depicting_digital_asset_internal?.map(
                    (resource) => resource.resourceId,
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
                    depictingDigitalAssetInternalData.depicting_digital_asset_internal =
                        depictingDigitalAssetInternalData.depicting_digital_asset_internal.filter(
                            (assetReference) =>
                                assetReference.resourceId !==
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
        <div class="conceptImages">
            <div
                v-for="resource in resources"
                :key="resource.resourceinstanceid"
                class="conceptImage"
            >
                <div class="header">
                    <label
                        for="conceptImage"
                        class="text"
                    >
                        <NonLocalizedStringWidget
                            node-alias="name_content"
                            graph-slug="digital_object_rdm_system"
                            :mode="VIEW"
                            :initial-value="resource.aliased_data.name?.aliased_data
                                .name_content
                                "
                        />
                    </label>
                    <div class="buttons">
                        <Button
                            icon="pi pi-file-edit"
                            @click="editResource(resource.resourceinstanceid)"
                        />
                        <Button
                            icon="pi pi-trash"
                            :aria-label="$gettext('Delete')"
                            severity="danger"
                            outlined
                            @click="confirmDelete(resource.resourceinstanceid)"
                        />
                    </div>
                </div>
                <FileListWidget
                    node-alias="content"
                    graph-slug="digital_object_rdm_system"
                    :initial-value="resource.aliased_data.content?.aliased_data.content
                        "
                    :mode="VIEW"
                />
                <div class="footer">
                    <NonLocalizedStringWidget
                        node-alias="statement_content"
                        graph-slug="digital_object_rdm_system"
                        :mode="VIEW"
                        :initial-value="resource.aliased_data.statement?.aliased_data
                            .statement_content
                            "
                    />
                </div>
            </div>
        </div>
    </div>
    </div>
</template>

<style scoped>
.conceptImages {
    display: flex;
    flex-direction: row;
    align-items: start;
    width: fit-content;
}

.conceptImage {
    width: 30rem;
    margin: 0 1rem;
}

.conceptImage .header {
    display: grid;
    grid-template-columns: 1fr auto;
    padding: 1rem 0;
}

.conceptImage .footer {
    padding: 1rem 0;
}

.conceptImage .header .text {
    display: flex;
    align-items: start;
    flex-direction: column;
}

.conceptImage .header .buttons {
    display: flex;
    justify-content: center;
}

.conceptImage .header .buttons button {
    margin: 0 0.5rem;
}

.conceptImages :deep(.mainImage) {}

.conceptImages :deep(.p-galleria) {
    border: none;
}
</style>
