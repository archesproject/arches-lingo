<script setup lang="ts">
import {
    computed,
    inject,
    onMounted,
    ref,
    toRaw,
    toRef,
    useId,
    type Ref,
} from "vue";

import Button from "primevue/button";
import { useGettext } from "vue3-gettext";
import { useRoute, useRouter } from "vue-router";
import { useToast } from "primevue/usetoast";

import {
    createScheme,
    fetchLingoResources,
    upsertLingoTile,
} from "@/arches_lingo/api.ts";
import { fetchLists } from "@/arches_references/api.ts";
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

import type {
    ControlledListItem,
    ControlledListItemResult,
    ControlledListResult,
    ResourceInstanceReference,
    ResourceInstanceResult,
    SchemeInstance,
    SchemeStatement,
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
        value?: SchemeStatement;
    }>(),
    {
        value: () => ({}) as SchemeStatement,
    },
);
const valueRef = toRef(props, "value");

const formValue = computed({
    get: () => valueRef.value,
    set: (newVal: SchemeStatement) => {
        valueRef.value = newVal;
    },
});

onMounted(async () => {
    initializeSelectOptions();
});

const languageOptions = ref<ControlledListItem[]>([]);
const typeOptions = ref<ControlledListItem[]>([]);
const metatypeOptions = ref<ControlledListItem[]>([]);
const eventTypeOptions = ref<ControlledListItem[]>([]);
const groupAndPersonOptions = ref<ResourceInstanceReference[]>();
const textualWorkOptions = ref<ResourceInstanceReference[]>();

const labelId = useId();
const labelLanguageId = useId();
const labelTypeId = useId();
const labelMetatypeId = useId();
const labelStartId = useId();
const labelEndId = useId();
const labelContributorId = useId();
const labelSourcesId = useId();
const labelWarrantId = useId();

const referenceNodeConfig = [
    {
        nodeAlias: "statement_language_n1",
        listRef: languageOptions,
        listName: "Languages",
    },
    {
        nodeAlias: "statement_type_n1",
        listRef: typeOptions,
        listName: "note",
    },
    {
        nodeAlias: "statement_type_metatype_n1",
        listRef: metatypeOptions,
        listName: "Metatypes",
    },
    {
        nodeAlias: "statement_data_assignment_type",
        listRef: eventTypeOptions,
        listName: "Event Types",
    },
];

function onUpdateString(node: keyof SchemeStatement, val: string) {
    (formValue.value[node] as unknown) = toRaw(val);
}

function onUpdateReferenceDatatype(
    node: keyof SchemeStatement,
    val: ControlledListItem[],
) {
    (formValue.value[node] as unknown) = val.map((item) => toRaw(item));
}

function onUpdateResourceInstance(
    node: keyof SchemeStatement,
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

async function save() {
    try {
        let newTileId;
        if (route.params.id === NEW) {
            const newSchemeInstance: SchemeInstance = {
                statement: [toRaw(formValue.value)],
            };
            const updated = await createScheme(newSchemeInstance);
            newTileId = updated.statement[0].tileid;
            await router.push({
                name: "scheme",
                params: { id: updated.resourceinstanceid },
            });
        } else {
            const updated = await upsertLingoTile(
                "scheme",
                "statement",
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
</script>

<template>
    <!-- Statement: string -->
    <label :for="labelId">{{ $gettext("Statement") }}</label>
    <NonLocalizedString
        :value="formValue?.statement_content_n1 ?? ''"
        :mode="EDIT"
        @update="(val) => onUpdateString('statement_content_n1', val)"
    />
    <!-- Statement Language: reference datatype -->
    <label :for="labelLanguageId">{{ $gettext("Statement Language") }}</label>
    <ReferenceDatatype
        :value="formValue?.statement_language_n1"
        :mode="EDIT"
        :multi-value="false"
        :options="languageOptions"
        :pt-aria-labeled-by="labelLanguageId"
        @update="
            (val) => onUpdateReferenceDatatype('statement_language_n1', val)
        "
    />
    <!-- Statement Type: reference datatype -->
    <label :for="labelTypeId">{{ $gettext("Statement Type") }}</label>
    <ReferenceDatatype
        :value="formValue?.statement_type_n1"
        :mode="EDIT"
        :multi-value="false"
        :options="typeOptions"
        :pt-aria-labeled-by="labelTypeId"
        @update="(val) => onUpdateReferenceDatatype('statement_type_n1', val)"
    />

    <!-- Statement Status Metatype: reference datatype -->
    <label :for="labelMetatypeId">{{ $gettext("Statement Metatype") }}</label>
    <ReferenceDatatype
        :value="formValue?.statement_type_metatype_n1"
        :mode="EDIT"
        :multi-value="false"
        :options="metatypeOptions"
        :pt-aria-labeled-by="labelMetatypeId"
        @update="
            (val) =>
                onUpdateReferenceDatatype('statement_type_metatype_n1', val)
        "
    />

    <!-- Statement Temporal Validity Start: date -->
    <label :for="labelStartId">{{
        $gettext("Statement Temporal Validity Start")
    }}</label>
    <DateDatatype
        :value="
            formValue?.statement_data_assignment_timespan_begin_of_the_begin
        "
        :mode="EDIT"
        :pt-aria-labeled-by="labelStartId"
        @update="
            (val) =>
                onUpdateString(
                    'statement_data_assignment_timespan_begin_of_the_begin',
                    val,
                )
        "
    />

    <!-- Statement Temporal Validity End: date -->
    <label :for="labelEndId">{{
        $gettext("Label Temporal Validity End")
    }}</label>
    <DateDatatype
        :value="formValue?.statement_data_assignment_timespan_end_of_the_end"
        :mode="EDIT"
        :pt-aria-labeled-by="labelEndId"
        @update="
            (val) =>
                onUpdateString(
                    'statement_data_assignment_timespan_end_of_the_end',
                    val,
                )
        "
    />

    <!-- Contributor: resource instance -->
    <label :for="labelContributorId">{{ $gettext("Contributor") }}</label>
    <ResourceInstanceRelationships
        :value="formValue?.statement_data_assignment_actor"
        :mode="EDIT"
        :options="groupAndPersonOptions"
        :pt-aria-labeled-by="labelContributorId"
        @update="
            (val) =>
                onUpdateResourceInstance(
                    'statement_data_assignment_actor',
                    val,
                    groupAndPersonOptions ?? [],
                )
        "
    />
    <!-- Sources: resource instance -->
    <label :for="labelSourcesId">{{ $gettext("Sources") }}</label>
    <ResourceInstanceRelationships
        :value="formValue?.statement_data_assignment_object_used"
        :mode="EDIT"
        :options="textualWorkOptions"
        :pt-aria-labeled-by="labelSourcesId"
        @update="
            (val) =>
                onUpdateResourceInstance(
                    'statement_data_assignment_object_used',
                    val,
                    textualWorkOptions ?? [],
                )
        "
    />
    <!-- Warrant Type: reference datatype -->
    <label :for="labelWarrantId">{{ $gettext("Warrant Type") }}</label>
    <ReferenceDatatype
        :value="formValue?.statement_data_assignment_type"
        :mode="EDIT"
        :multi-value="false"
        :options="eventTypeOptions"
        :pt-aria-labeled-by="labelWarrantId"
        @update="
            (val) =>
                onUpdateReferenceDatatype('statement_data_assignment_type', val)
        "
    />
    <Button
        :label="$gettext('Update')"
        @click="save"
    ></Button>
</template>
