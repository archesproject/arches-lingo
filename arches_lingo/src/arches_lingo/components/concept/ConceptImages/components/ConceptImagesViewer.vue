<script setup lang="ts">
import { inject, ref, onMounted } from "vue";
import { useGettext } from "vue3-gettext";

import Button from "primevue/button";

import FileListWidget from "@/arches_component_lab/widgets/FileListWidget/FileListWidget.vue";

import { DANGER, SECONDARY, VIEW } from "@/arches_lingo/constants.ts";
import { useConfirm } from "primevue/useconfirm";

import type {
    ConceptImages,
    DigitalObjectInstance,
} from "@/arches_lingo/types.ts";
import { fetchLingoResourcesBatch } from "@/arches_lingo/api.ts";
import NonLocalizedStringWidget from "@/arches_component_lab/widgets/NonLocalizedStringWidget/NonLocalizedStringWidget.vue";

const props = defineProps<{
    tileData: ConceptImages | undefined;
    componentName: string;
    sectionTitle: string;
    graphSlug: string;
    nodegroupAlias: string;
}>();

const openEditor = inject<(componentName: string) => void>("openEditor");

const isLoading = ref(true);
const resources = ref<DigitalObjectInstance[]>();
const { $gettext } = useGettext();
const confirm = useConfirm();

onMounted(async () => {
    if (props.tileData) {

        resources.value = await fetchLingoResourcesBatch(
            "digital_object_rdm_system",
            props.tileData.aliased_data.depicting_digital_asset_internal.map(
                (resource) => resource.resourceId,
            ),
        );
        isLoading.value = false;
    }
});
function confirmDelete() {
    confirm.require({
        header: $gettext("Confirmation"),
        message: $gettext("Do you want to delete this concept image?"),
        accept: () => {
            console.log("do delete");
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
</script>

<template>
    <ProgressSpinner
        v-if="isLoading"
        style="width: 100%"
    />
    <template v-else>
        <div class="section-header">
            <h2>{{ props.sectionTitle }}</h2>
            <Button
                :label="$gettext('Add New Concept Image')"
                @click="openEditor!(props.componentName)"
            ></Button>
        </div>
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
                            :initial-value="resource.aliased_data.name.aliased_data.name_content
                                "
                        />
                    </label>
                    <div class="buttons">
                        <Button
                            icon="pi pi-file-edit"
                            @click="openEditor!(props.componentName)"
                        />
                        <Button
                            icon="pi pi-trash"
                            :aria-label="$gettext('Delete')"
                            severity="danger"
                            outlined
                            @click="confirmDelete()"
                        />
                    </div>
                </div>
                <FileListWidget
                    node-alias="content"
                    graph-slug="digital_object_rdm_system"
                    :initial-value="resource.aliased_data.content?.aliased_data.content
                        "
                    :mode="VIEW"
                    class="conceptImage"
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
    </template>
</template>

<style scoped>
.section-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    border-bottom: 0.125rem solid var(--p-menubar-border-color);
}

.conceptImages {
    display: flex;
    flex-direction: row;
    align-items: start;
}

.conceptImage {
    display: grid;
    grid-template-rows: auto auto auto;
    margin: 2rem 5rem;
    flex: 1 1 0;
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
