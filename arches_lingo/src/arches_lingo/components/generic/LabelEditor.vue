<script setup lang="ts">
import { computed, inject, onMounted, ref, toRaw, toRef, useId } from "vue";

import Button from "primevue/button";
import { useGettext } from "vue3-gettext";
import { useRoute, useRouter } from "vue-router";
import { useToast } from "primevue/usetoast";

import { fetchLists } from "@/arches_references/api.ts";

import {
    createScheme,
    fetchLingoResources,
    upsertLingoTile,
} from "@/arches_lingo/api.ts";

import DateDatatype from "@/arches_lingo/components/generic/DateDatatype.vue";
import NonLocalizedString from "@/arches_lingo/components/generic/NonLocalizedString.vue";
import ReferenceDatatype from "@/arches_lingo/components/generic/ReferenceDatatype.vue";
import ResourceInstanceRelationships from "@/arches_lingo/components/generic/ResourceInstanceRelationships.vue";

import {
    EDIT,
    ERROR,
    NEW,
    selectedLanguageKey,
} from "@/arches_lingo/constants.ts";

import type { Ref } from "vue";
import type {
    AppellativeStatus,
    ControlledListResult,
    ControlledListItem,
    ControlledListItemResult,
    ResourceInstanceReference,
    ResourceInstanceResult,
    SchemeInstance,
} from "@/arches_lingo/types.ts";
import type { Language } from "@/arches_vue_utils/types.ts";

const emit = defineEmits(["update"]);
const toast = useToast();
const route = useRoute();
const router = useRouter();
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
const valueRef = toRef(props, "value");
const formValue = computed({
    get: () => valueRef.value,
    set: (newVal: AppellativeStatus) => {
        valueRef.value = newVal;
    },
});

const languageOptions = ref<ControlledListItem[]>([]);
const typeOptions = ref<ControlledListItem[]>([]);
const statusOptions = ref<ControlledListItem[]>([]);
const metatypeOptions = ref<ControlledListItem[]>([]);
const eventTypeOptions = ref<ControlledListItem[]>([]);
const groupAndPersonOptions = ref<ResourceInstanceReference[]>();
const textualWorkOptions = ref<ResourceInstanceReference[]>();

const labelId = useId();
const labelLanguageId = useId();
const labelTypeId = useId();
const labelStatusId = useId();
const labelMetatypeId = useId();
const labelStartId = useId();
const labelEndId = useId();
const labelContributorId = useId();
const labelSourcesId = useId();
const labelWarrantId = useId();

const referenceNodeConfig = [
    {
        nodeAlias: "appellative_status_ascribed_name_language",
        listRef: languageOptions,
        listName: "Languages",
    },
    {
        nodeAlias: "appellative_status_ascribed_relation",
        listRef: typeOptions,
        listName: "label",
    },
    {
        nodeAlias: "appellative_status_status",
        listRef: statusOptions,
        listName: "Statuteses",
    },
    {
        nodeAlias: "appellative_status_status_metatype",
        listRef: metatypeOptions,
        listName: "Metatypes",
    },
    {
        nodeAlias: "appellative_status_data_assignment_type",
        listRef: eventTypeOptions,
        listName: "Event Types",
    },
];

function onUpdateString(node: keyof AppellativeStatus, val: string) {
    (formValue.value[node] as unknown) = toRaw(val);
}

function onUpdateReferenceDatatype(
    node: keyof AppellativeStatus,
    val: ControlledListItem[],
) {
    (formValue.value[node] as unknown) = val.map((item) => toRaw(item));
}

function onUpdateResourceInstance(
    node: keyof AppellativeStatus,
    val: string[],
    options: ResourceInstanceReference[],
) {
    if (val.length > 0) {
        const selectedOptions = options.filter((option) =>
            val.includes(option.resourceId),
        );
        (formValue.value[node] as unknown) = selectedOptions;
    }
}

async function save() {
    try {
        let newTileId;
        if (route.params.id === NEW) {
            const newSchemeInstance: SchemeInstance = {
                appellative_status: [toRaw(formValue.value)],
            };
            const updated = await createScheme(newSchemeInstance);
            newTileId = updated.appellative_status[0].tileid;
            await router.push({
                name: "scheme",
                params: { id: updated.resourceinstanceid },
            });
        } else {
            const updated = await upsertLingoTile(
                "scheme",
                "appellative_status",
                {
                    resourceinstance: route.params.id as string,
                    ...formValue.value,
                },
                formValue.value.tileid,
            );
            newTileId = updated.tileid;
        }
        emit("update", newTileId);
    } catch (error) {
        toast.add({
            severity: ERROR,
            summary: $gettext("Error saving scheme"),
            detail: (error as Error).message,
        });
    }
}

async function getControlledLists() {
    let parsed;
    try {
        parsed = await fetchLists(
            referenceNodeConfig.map((node) => node.nodeAlias),
        );
    } catch (error) {
        toast.add({
            severity: ERROR,
            summary: $gettext("Error"),
            detail:
                error instanceof Error
                    ? error.message
                    : $gettext("Could not fetch the controlled list options"),
        });
        return [];
    }
    const controlledLists = parsed.controlled_lists;
    referenceNodeConfig.forEach((node) => {
        const matchingList = controlledLists.find(
            (list: ControlledListResult) => list.name === node.listName,
        );
        const options = matchingList.items.map(
            (item: ControlledListItemResult): ControlledListItem => ({
                list_id: item.list_id,
                uri: item.uri,
                labels: item.values,
            }),
        );
        node.listRef.value = options;
    });
}

async function getResourceInstanceOptions(
    fetchOptions: () => Promise<ResourceInstanceResult[]>,
): Promise<ResourceInstanceReference[]> {
    let options;
    try {
        options = await fetchOptions();
    } catch (error) {
        toast.add({
            severity: ERROR,
            summary: $gettext("Error"),
            detail:
                error instanceof Error
                    ? error.message
                    : $gettext("Could not fetch the resource instance options"),
        });
        return [];
    }
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
async function initializeSelectOptions() {
    getControlledLists();
    groupAndPersonOptions.value = await getResourceInstanceOptions(() =>
        fetchLingoResources("group"),
    );
    groupAndPersonOptions.value = [
        ...(groupAndPersonOptions.value || []),
        ...(await getResourceInstanceOptions(() =>
            fetchLingoResources("person"),
        )),
    ];
    textualWorkOptions.value = await getResourceInstanceOptions(() =>
        fetchLingoResources("textual_work"),
    );
}

onMounted(initializeSelectOptions);
</script>

<template>
    <label :for="labelId">{{ $gettext("Label") }}</label>
    <NonLocalizedString
        :value="formValue?.appellative_status_ascribed_name_content"
        :mode="EDIT"
        :pass-thru-id="labelId"
        @update="
            (val) =>
                onUpdateString('appellative_status_ascribed_name_content', val)
        "
    />
    <p :id="labelLanguageId">{{ $gettext("Label Language") }}</p>
    <ReferenceDatatype
        :value="formValue?.appellative_status_ascribed_name_language"
        :mode="EDIT"
        :multi-value="false"
        :options="languageOptions"
        :pt-aria-labeled-by="labelLanguageId"
        @update="
            (val) =>
                onUpdateReferenceDatatype(
                    'appellative_status_ascribed_name_language',
                    val,
                )
        "
    />
    <p :id="labelTypeId">{{ $gettext("Label Type") }}</p>
    <ReferenceDatatype
        :value="formValue?.appellative_status_ascribed_relation"
        :mode="EDIT"
        :multi-value="false"
        :options="typeOptions"
        :pt-aria-labeled-by="labelTypeId"
        @update="
            (val) =>
                onUpdateReferenceDatatype(
                    'appellative_status_ascribed_relation',
                    val,
                )
        "
    />
    <p :id="labelStatusId">{{ $gettext("Label Status") }}</p>
    <ReferenceDatatype
        :value="formValue?.appellative_status_status"
        :mode="EDIT"
        :multi-value="false"
        :options="statusOptions"
        :pt-aria-labeled-by="labelStatusId"
        @update="
            (val) => onUpdateReferenceDatatype('appellative_status_status', val)
        "
    />
    <p :id="labelMetatypeId">{{ $gettext("Label Metatype") }}</p>
    <ReferenceDatatype
        :value="formValue?.appellative_status_status_metatype"
        :mode="EDIT"
        :multi-value="false"
        :options="metatypeOptions"
        :pt-aria-labeled-by="labelMetatypeId"
        @update="
            (val) =>
                onUpdateReferenceDatatype(
                    'appellative_status_status_metatype',
                    val,
                )
        "
    />
    <p :id="labelStartId">{{ $gettext("Label Temporal Validity Start") }}</p>
    <DateDatatype
        :value="formValue?.appellative_status_timespan_begin_of_the_begin"
        :mode="EDIT"
        :pt-aria-labeled-by="labelStartId"
        @update="
            (val) =>
                onUpdateString(
                    'appellative_status_timespan_begin_of_the_begin',
                    val,
                )
        "
    />
    <p :id="labelEndId">{{ $gettext("Label Temporal Validity End") }}</p>
    <DateDatatype
        :value="formValue?.appellative_status_timespan_end_of_the_end"
        :mode="EDIT"
        :pt-aria-labeled-by="labelEndId"
        @update="
            (val) =>
                onUpdateString(
                    'appellative_status_timespan_end_of_the_end',
                    val,
                )
        "
    />
    <p :id="labelContributorId">{{ $gettext("Contributor") }}</p>
    <ResourceInstanceRelationships
        :value="formValue?.appellative_status_data_assignment_actor"
        :mode="EDIT"
        :options="groupAndPersonOptions"
        :pt-aria-labeled-by="labelContributorId"
        @update="
            (val) =>
                onUpdateResourceInstance(
                    'appellative_status_data_assignment_actor',
                    val,
                    groupAndPersonOptions ?? [],
                )
        "
    />
    <p :id="labelSourcesId">{{ $gettext("Sources") }}</p>
    <ResourceInstanceRelationships
        :value="formValue?.appellative_status_data_assignment_object_used"
        :mode="EDIT"
        :options="textualWorkOptions"
        :pt-aria-labeled-by="labelSourcesId"
        @update="
            (val) =>
                onUpdateResourceInstance(
                    'appellative_status_data_assignment_object_used',
                    val,
                    textualWorkOptions ?? [],
                )
        "
    />
    <p :id="labelWarrantId">{{ $gettext("Warrant Type") }}</p>
    <ReferenceDatatype
        :value="formValue?.appellative_status_data_assignment_type"
        :mode="EDIT"
        :multi-value="false"
        :options="eventTypeOptions"
        :pt-aria-labeled-by="labelWarrantId"
        @update="
            (val) =>
                onUpdateReferenceDatatype(
                    'appellative_status_data_assignment_type',
                    val,
                )
        "
    />
    <Button
        :label="$gettext('Update')"
        @click="save"
    />
</template>

<style scoped>
p {
    margin: 0;
}
</style>
