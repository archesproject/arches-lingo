<script setup lang="ts">
import { computed, inject } from "vue";
import { useGettext } from "vue3-gettext";

import Button from "primevue/button";

import NonLocalizedTextAreaWidget from "@/arches_component_lab/widgets/NonLocalizedTextAreaWidget/NonLocalizedTextAreaWidget.vue";
import ReferenceSelectWidget from "@/arches_controlled_lists/widgets/ReferenceSelectWidget/ReferenceSelectWidget.vue";
import ResourceInstanceMultiSelectWidget from "@/arches_component_lab/widgets/ResourceInstanceMultiSelectWidget/ResourceInstanceMultiSelectWidget.vue";

import { VIEW } from "@/arches_lingo/constants.ts";

import type { SchemeRights } from "@/arches_lingo/types";

const props = defineProps<{
    tileData: SchemeRights | undefined;
    graphSlug: string;
    componentName: string;
    sectionTitle: string;
}>();

const { $gettext } = useGettext();

const openEditor =
    inject<(componentName: string, tileId: string | undefined) => void>(
        "openEditor",
    );

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
                :label="buttonLabel"
                class="add-button"
                @click="
                    openEditor!(props.componentName, props.tileData?.tileid)
                "
            ></Button>
        </div>

        <div v-if="props.tileData">
            <ResourceInstanceMultiSelectWidget
                node-alias="right_holder"
                :graph-slug="props.graphSlug"
                :value="
                    props.tileData?.aliased_data.right_holder?.interchange_value
                "
                :mode="VIEW"
            />
            <ReferenceSelectWidget
                node-alias="right_type"
                :graph-slug="props.graphSlug"
                :value="
                    props.tileData?.aliased_data.right_type?.interchange_value
                "
                :mode="VIEW"
            />
            <NonLocalizedTextAreaWidget
                node-alias="right_statement_content"
                :graph-slug="props.graphSlug"
                :value="
                    props.tileData?.aliased_data.right_statement?.aliased_data
                        ?.right_statement_content?.display_value
                "
                :mode="VIEW"
            />
            <ReferenceSelectWidget
                node-alias="right_statement_language"
                :graph-slug="props.graphSlug"
                :value="
                    props.tileData?.aliased_data.right_statement?.aliased_data
                        .right_statement_language?.interchange_value
                "
                :mode="VIEW"
            />
            <ReferenceSelectWidget
                node-alias="right_statement_type"
                :graph-slug="props.graphSlug"
                :value="
                    props.tileData?.aliased_data.right_statement?.aliased_data
                        .right_statement_type?.interchange_value
                "
                :mode="VIEW"
            />
            <ReferenceSelectWidget
                node-alias="right_statement_type_metatype"
                :graph-slug="props.graphSlug"
                :value="
                    props.tileData?.aliased_data.right_statement?.aliased_data
                        .right_statement_type_metatype?.interchange_value
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
