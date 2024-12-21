<script setup lang="ts">
import { inject, onMounted, ref, type Ref } from "vue";
import { useRoute } from "vue-router";
import { useGettext } from "vue3-gettext";
import SchemeReportSection from "@/arches_lingo/components/scheme/report/SchemeSection.vue";
import {
    fetchSchemeRights,
    updateSchemeRights,
    fetchPersonRdmSystemList,
    fetchGroupRdmSystemList,
} from "@/arches_lingo/api.ts";
import type {
    DataComponentMode,
    ResourceInstanceReference,
    ResourceInstanceResult,
    SchemeInstance,
} from "@/arches_lingo/types";
import { selectedLanguageKey, VIEW, EDIT } from "@/arches_lingo/constants.ts";
import ResourceInstanceRelationships from "../../generic/ResourceInstanceRelationships.vue";
import ControlledListItem from "../../generic/ControlledListItem.vue";
import type { Language } from "@/arches_vue_utils/types.ts";

onMounted(async () => {
    getSectionValue();
});

defineEmits(["openEditor"]);
defineProps<{
    mode?: DataComponentMode;
}>();

const schemeRights = ref<SchemeInstance>();
const route = useRoute();
const actorRdmOptions = ref<ResourceInstanceReference[]>();
const selectedLanguage = inject(selectedLanguageKey) as Ref<Language>;

async function getOptions(): Promise<ResourceInstanceReference[]> {
    const options_person = await fetchPersonRdmSystemList();
    const options_group = await fetchGroupRdmSystemList();
    const options = options_person.concat(options_group);

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
};
function onSchemeRightsUpdate(val: string[]) {
    const schemeRightsValue = schemeRights.value!;
    if (actorRdmOptions.value) {
        const options = actorRdmOptions.value?.filter((option) =>
            val.includes(option.resourceId),
        );
        if (!schemeRightsValue?.rights) {
            schemeRightsValue.rights = {
                right_holder: options,
                right_type: [],
            };
        } else {
            schemeRightsValue.rights.right_holder = options;
        }
    }
};
async function save() {
    await updateSchemeRights(
        route.params.id as string,
        schemeRights.value as SchemeInstance,
    );
};
async function getSectionValue() {
    const options = !actorRdmOptions.value
        ? await getOptions()
        : actorRdmOptions.value;

    const scheme = await fetchSchemeRights(route.params.id as string);
    
    const hydratedResults = options.map((option) => {
        const savedSource = scheme.rights?.right_holder.find(
            (source: ResourceInstanceReference) =>
                source.resourceId === option.resourceId,
        );
        if (savedSource) {
            return savedSource;
        } else {
            return option;
        }
    });
    actorRdmOptions.value = hydratedResults;
    schemeRights.value = scheme;
};

defineExpose({ save, getSectionValue });
const { $gettext } = useGettext();
</script>

<template>
    <div>
        <div v-if="!mode || mode === VIEW">
            <SchemeReportSection
                :title-text="$gettext('Scheme Rights')"
                @open-editor="$emit('openEditor')"
            >
                <h4>{{ $gettext('Rights Holders') }}</h4>
                <ResourceInstanceRelationships
                    :value="schemeRights?.rights?.right_holder"
                    :mode="VIEW"
                />
                <h4>{{ $gettext('Rights Type') }}</h4>
                <!-- <ControlledListItem
                    :value="schemeRights?.rights?.right_type"
                    :mode="VIEW"
                /> -->
            </SchemeReportSection>
        </div>
        <div v-if="mode === EDIT">
            <h4>{{ $gettext('Rights Holders') }}</h4>
            <ResourceInstanceRelationships
            :value="schemeRights?.rights?.right_holder"
                :options="actorRdmOptions"
                :mode="EDIT"
                @update="onSchemeRightsUpdate"
            />
            <h4>{{ $gettext('Rights Type') }}</h4>
            <!-- <ControlledListItem
                :value="schemeRights?.rights?.right_type"
                :mode="EDIT"
            /> -->
        </div>
    </div>
</template>
