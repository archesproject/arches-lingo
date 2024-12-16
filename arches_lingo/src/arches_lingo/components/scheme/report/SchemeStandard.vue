<script setup lang="ts">
import { inject, onMounted, ref, type Ref } from "vue";
import { useRoute } from "vue-router";
import { useGettext } from "vue3-gettext";
import type {
    DataComponentMode,
    ResourceInstanceReference,
    ResourceInstanceResult,
    SchemeInstance,
} from "@/arches_lingo/types";
import SchemeReportSection from "@/arches_lingo/components/scheme/report/SchemeSection.vue";
import {
    fetchSchemeCreation,
    fetchTextualWorkRdmSystemList,
    updateSchemeCreation,
} from "@/arches_lingo/api.ts";
import ResourceInstanceRelationships from "../../generic/ResourceInstanceRelationships.vue";
import {
    selectedLanguageKey,
    VIEW,
    EDIT,
    OPEN_EDITOR,
} from "@/arches_lingo/constants.ts";
import type { Language } from "@/arches_vue_utils/types.ts";

const schemeInstance = ref<SchemeInstance>();
const textualWorkOptions = ref<ResourceInstanceReference[]>();
const route = useRoute();
const selectedLanguage = inject(selectedLanguageKey) as Ref<Language>;
const { $gettext } = useGettext();

const { mode = VIEW } = defineProps<{
    mode?: DataComponentMode;
}>();

const emits = defineEmits([OPEN_EDITOR]);

defineExpose({ save, getSectionValue });

onMounted(async () => {
    getSectionValue();
});

async function getOptions(): Promise<ResourceInstanceReference[]> {
    const options = await fetchTextualWorkRdmSystemList();
    const results = options.map((option: ResourceInstanceResult) => {
        const result: ResourceInstanceReference = {
            display_value: option.descriptors[selectedLanguage.value.code].name,
            resourceId: option.resourceinstanceid,
            ontologyProperty: "ac41d9be-79db-4256-b368-2f4559cfbe55",
            inverseOntologyProperty: "ac41d9be-79db-4256-b368-2f4559cfbe55",
        };
        return result;
    });
    return results;
}

async function save() {
    await updateSchemeCreation(
        route.params.id as string,
        schemeInstance.value as SchemeInstance,
    );

    getSectionValue();
}

async function getSectionValue() {
    const options = !textualWorkOptions.value
        ? await getOptions()
        : textualWorkOptions.value;

    const scheme = await fetchSchemeCreation(route.params.id as string);

    const hydratedResults = options.map((option) => {
        const savedSource = scheme.creation?.creation_sources.find(
            (source: ResourceInstanceReference) =>
                source.resourceId === option.resourceId,
        );
        if (savedSource) {
            return savedSource;
        } else {
            return option;
        }
    });
    textualWorkOptions.value = hydratedResults;
    schemeInstance.value = scheme;
}

function onCreationUpdate(val: string[]) {
    const schemeInstanceValue = schemeInstance.value!; // should never be null when updating
    if (textualWorkOptions.value) {
        const options = textualWorkOptions.value?.filter((option) =>
            val.includes(option.resourceId),
        );
        if (!schemeInstanceValue?.creation) {
            schemeInstanceValue.creation = { creation_sources: options };
        } else {
            schemeInstanceValue.creation.creation_sources = options;
        }
    }
}
</script>

<template>
    <div v-if="!mode || mode === VIEW">
        <SchemeReportSection
            :title-text="$gettext('Scheme Standards Followed')"
            @open-editor="emits(OPEN_EDITOR)"
        >
            <ResourceInstanceRelationships
                :value="schemeInstance?.creation?.creation_sources"
                :mode="VIEW"
            />
            <!-- Discussion of namespace_type indicated it should not be displayed or edited manually,
                 if this changes, the ControlledListItem widget can be used.-->
        </SchemeReportSection>
    </div>
    <div v-if="mode === EDIT">
        <ResourceInstanceRelationships
            :value="schemeInstance?.creation?.creation_sources"
            :options="textualWorkOptions"
            :mode="EDIT"
            @update="onCreationUpdate"
        />
    </div>
</template>
