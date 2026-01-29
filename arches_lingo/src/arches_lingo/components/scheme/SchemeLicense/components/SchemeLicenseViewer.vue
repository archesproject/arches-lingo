<script setup lang="ts">
import { computed, inject } from "vue";
import { useGettext } from "vue3-gettext";

import Button from "primevue/button";

import GenericWidget from "@/arches_component_lab/generics/GenericWidget/GenericWidget.vue";

import { VIEW } from "@/arches_lingo/constants.ts";

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

const buttonLabel = computed(() => {
    if (props.tileData) {
        return $gettext("Edit Rights");
    } else {
        return $gettext("Add Rights");
    }
});
</script>
<template>
    <div class="viewer-section">
        <div class="section-header">
            <h2>{{ props.sectionTitle }}</h2>

            <Button
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
                class="add-button"
                icon="pi pi-plus-circle"
                @click="
                    openEditor!(props.componentName, props.tileData?.tileid)
                "
            ></Button>
        </div>

        <div v-if="props.tileData">
            <GenericWidget
                node-alias="right_holder"
                :graph-slug="props.graphSlug"
                :aliased-node-data="props.tileData?.aliased_data.right_holder"
                :mode="VIEW"
            />
            <GenericWidget
                node-alias="right_type"
                :graph-slug="props.graphSlug"
                :aliased-node-data="props.tileData?.aliased_data.right_type"
                :mode="VIEW"
            />
            <GenericWidget
                node-alias="right_statement_content"
                :graph-slug="props.graphSlug"
                :aliased-node-data="
                    props.tileData?.aliased_data.right_statement?.aliased_data
                        ?.right_statement_content
                "
                :mode="VIEW"
            />
            <GenericWidget
                node-alias="right_statement_language"
                :graph-slug="props.graphSlug"
                :aliased-node-data="
                    props.tileData?.aliased_data.right_statement?.aliased_data
                        .right_statement_language
                "
                :mode="VIEW"
            />
            <GenericWidget
                node-alias="right_statement_type"
                :graph-slug="props.graphSlug"
                :aliased-node-data="
                    props.tileData?.aliased_data.right_statement?.aliased_data
                        .right_statement_type
                "
                :mode="VIEW"
            />
            <GenericWidget
                node-alias="right_statement_type_metatype"
                :graph-slug="props.graphSlug"
                :aliased-node-data="
                    props.tileData?.aliased_data.right_statement?.aliased_data
                        .right_statement_type_metatype
                "
                :mode="VIEW"
            />
        </div>
        <div
            v-else
            class="section-message"
        >
            {{ $gettext("No Scheme Rights were found.") }}
        </div>
    </div>
</template>
