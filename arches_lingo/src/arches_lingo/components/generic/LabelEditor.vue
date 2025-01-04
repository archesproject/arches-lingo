<script setup lang="ts">
import { defineProps, inject, onMounted, ref, toRaw, type Ref } from "vue";
import Button from "primevue/button";
import { useGettext } from "vue3-gettext";
import { useRoute } from "vue-router";
import { useToast } from "primevue/usetoast";

import {
    fetchControlledListOptions,
    fetchGroupRdmSystemList,
    fetchPersonRdmSystemList,
    fetchTextualWorkRdmSystemList,
    updateSchemeLabel,
} from "@/arches_lingo/api.ts";

import NonLocalizedString from "@/arches_lingo/components/generic/NonLocalizedString.vue";
import ReferenceDatatype from "@/arches_lingo/components/generic/ReferenceDatatype.vue";
import ResourceInstanceRelationships from "@/arches_lingo/components/generic/ResourceInstanceRelationships.vue";

import {
    EDIT,
    ERROR,
    EVENT_TYPES_CONTROLLED_LIST,
    LABEL_CONTROLLED_LIST,
    LANGUAGE_CONTROLLED_LIST,
    METATYPES_CONTROLLED_LIST,
    selectedLanguageKey,
    STATUSES_CONTROLLED_LIST,
} from "@/arches_lingo/constants.ts";

import type {
    AppellativeStatus,
    ControlledListItem,
    ControlledListItemResult,
    ResourceInstanceReference,
    ResourceInstanceResult,
} from "@/arches_lingo/types.ts";
import type { Language } from "@/arches_vue_utils/types.ts";

const emit = defineEmits(["update"]);
const toast = useToast();
const route = useRoute();
const selectedLanguage = inject(selectedLanguageKey) as Ref<Language>;
const { $gettext } = useGettext();

const props = withDefaults(
    defineProps<{
        value?: AppellativeStatus;
    }>(),
    {
        value: () => ({}) as AppellativeStatus,
    },
);
const value = ref(props.value);

const languageOptions = ref<ControlledListItem[]>([]);
const typeOptions = ref<ControlledListItem[]>([]);
const statusOptions = ref<ControlledListItem[]>([]);
const metatypeOptions = ref<ControlledListItem[]>([]);
const eventTypeOptions = ref<ControlledListItem[]>([]);
const groupAndPersonOptions = ref<ResourceInstanceReference[]>();
const textualWorkOptions = ref<ResourceInstanceReference[]>();

function onUpdate(
    node: keyof AppellativeStatus,
    val: ControlledListItem[] | ResourceInstanceReference[] | string,
) {
    if (Array.isArray(val)) {
        (value.value[node] as unknown) = val.map((item) => toRaw(item));
    } else {
        (value.value[node] as unknown) = toRaw(val);
    }
}

async function save() {
    try {
        await updateSchemeLabel(
            route.params.id as string,
            value.value.tileid as string,
            value.value,
        );
        emit("update");
    } catch (error) {
        toast.add({
            severity: ERROR,
            summary: $gettext("Error saving scheme"),
            detail: (error as Error).message,
        });
    }
}

async function getControlledListOptions(
    listId: string,
): Promise<ControlledListItem[]> {
    const parsed = await fetchControlledListOptions(listId);
    const options = parsed.items.map(
        (item: ControlledListItemResult): ControlledListItem => ({
            list_id: item.list_id,
            uri: item.uri,
            labels: item.values,
        }),
    );
    return options;
}

async function getResourceInstanceOptions(
    fetchOptions: () => Promise<ResourceInstanceResult[]>,
): Promise<ResourceInstanceReference[]> {
    const options = await fetchOptions();
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

onMounted(async () => {
    const [languageOpts, typeOpts, statusOpts, metatypeOpts, eventTypeOpts] =
        await Promise.all([
            getControlledListOptions(LANGUAGE_CONTROLLED_LIST),
            getControlledListOptions(LABEL_CONTROLLED_LIST),
            getControlledListOptions(STATUSES_CONTROLLED_LIST),
            getControlledListOptions(METATYPES_CONTROLLED_LIST),
            getControlledListOptions(EVENT_TYPES_CONTROLLED_LIST),
        ]);

    languageOptions.value = languageOpts;
    typeOptions.value = typeOpts;
    statusOptions.value = statusOpts;
    metatypeOptions.value = metatypeOpts;
    eventTypeOptions.value = eventTypeOpts;
    groupAndPersonOptions.value = await getResourceInstanceOptions(
        fetchGroupRdmSystemList,
    );
    groupAndPersonOptions.value = [
        ...(groupAndPersonOptions.value || []),
        ...(await getResourceInstanceOptions(fetchPersonRdmSystemList)),
    ];
    textualWorkOptions.value = await getResourceInstanceOptions(
        fetchTextualWorkRdmSystemList,
    );
});
</script>

<template>
    <!-- Label: string -->
    <label for="">{{ $gettext("Label") }}</label>
    <NonLocalizedString
        :value="value?.appellative_status_ascribed_name_content ?? ''"
        :mode="EDIT"
        @update="
            (val) => onUpdate('appellative_status_ascribed_name_content', val)
        "
    />
    <!-- Label Language: reference datatype -->
    <label for="">{{ $gettext("Label Language") }}</label>
    <ReferenceDatatype
        :value="value?.appellative_status_ascribed_name_language"
        :mode="EDIT"
        :multi-value="false"
        :options="languageOptions"
        @update="
            (val) => onUpdate('appellative_status_ascribed_name_language', val)
        "
    />
    <!-- Label Type: reference datatype -->
    <label for="">{{ $gettext("Label Type") }}</label>
    <ReferenceDatatype
        :value="value?.appellative_status_ascribed_relation"
        :mode="EDIT"
        :multi-value="false"
        :options="typeOptions"
        @update="(val) => onUpdate('appellative_status_ascribed_relation', val)"
    />
    <!-- Label Status: reference datatype -->
    <label for="">{{ $gettext("Label Status") }}</label>
    <ReferenceDatatype
        :value="value?.appellative_status_status"
        :mode="EDIT"
        :multi-value="false"
        :options="statusOptions"
        @update="(val) => onUpdate('appellative_status_status', val)"
    />
    <!-- Label Status Metatype: reference datatype -->
    <label for="">{{ $gettext("Label Metatype") }}</label>
    <ReferenceDatatype
        :value="value?.appellative_status_status_metatype"
        :mode="EDIT"
        :multi-value="false"
        :options="metatypeOptions"
        @update="(val) => onUpdate('appellative_status_status_metatype', val)"
    />
    <!-- Label Temporal Validity Start: date -->
    <label for="">{{ $gettext("Label Temporal Validity Start") }}</label>

    <!-- Label Temporal Validity End: date -->
    <label for="">{{ $gettext("Label Temporal Validity End") }}</label>

    <!-- Contributor: resource instance -->
    <label for="">{{ $gettext("Contributor") }}</label>
    <ResourceInstanceRelationships
        :value="value?.appellative_status_data_assignment_actor"
        :mode="EDIT"
        :options="groupAndPersonOptions"
        @update="
            (val) => onUpdate('appellative_status_data_assignment_actor', val)
        "
    />
    <!-- Sources: resource instance -->
    <label for="">{{ $gettext("Sources") }}</label>
    <ResourceInstanceRelationships
        :value="value?.appellative_status_data_assignment_object_used"
        :mode="EDIT"
        :options="textualWorkOptions"
        @update="
            (val) =>
                onUpdate('appellative_status_data_assignment_object_used', val)
        "
    />
    <!-- Warrant Type: reference datatype -->
    <label for="">{{ $gettext("Warrant Type") }}</label>
    <ReferenceDatatype
        :value="value?.appellative_status_data_assignment_type"
        :mode="EDIT"
        :multi-value="false"
        :options="eventTypeOptions"
        @update="
            (val) => onUpdate('appellative_status_data_assignment_type', val)
        "
    />
    <Button
        :label="$gettext('Update')"
        @click="save"
    ></Button>
</template>
