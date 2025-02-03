<script setup lang="ts">
import { inject, onMounted, ref, type Ref } from "vue";
import { useRoute, useRouter } from "vue-router";
import { useGettext } from "vue3-gettext";

import Button from "primevue/button";
import { useToast } from "primevue/usetoast";

import ResourceInstanceRelationships from "@/arches_lingo/components/generic/ResourceInstanceRelationships.vue";
import SchemeReportSection from "@/arches_lingo/components/scheme/report/SchemeSection.vue";
import {
    createScheme,
    fetchLingoResourcePartial,
    fetchLingoResources,
    updateLingoResource,
} from "@/arches_lingo/api.ts";
import {
    selectedLanguageKey,
    VIEW,
    EDIT,
    OPEN_EDITOR,
    NEW,
    UPDATED,
    ERROR,
} from "@/arches_lingo/constants.ts";

import type { Language } from "@/arches_vue_utils/types.ts";
import type {
    DataComponentMode,
    ResourceInstanceReference,
    ResourceInstanceResult,
    SchemeInstance,
} from "@/arches_lingo/types";

const toast = useToast();
const schemeInstance = ref<SchemeInstance>({});
const textualWorkOptions = ref<ResourceInstanceReference[]>();
const route = useRoute();
const router = useRouter();
const selectedLanguage = inject(selectedLanguageKey) as Ref<Language>;
const { $gettext } = useGettext();

const { mode = VIEW } = defineProps<{
    mode?: DataComponentMode;
}>();

const emit = defineEmits([OPEN_EDITOR, UPDATED]);

defineExpose({ getSectionValue });

onMounted(async () => {
    getSectionValue();
});

async function getOptions(): Promise<ResourceInstanceReference[]> {
    const options = await fetchLingoResources("textual_work");
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
    try {
        let updated;
        if (route.params.id === NEW) {
            updated = await createScheme(schemeInstance.value);
            await router.push({
                name: "scheme",
                params: { id: updated.resourceinstanceid },
            });
        } else {
            updated = await updateLingoResource(
                "scheme",
                route.params.id as string,
                schemeInstance.value,
            );
        }
        schemeInstance.value = updated;
        emit(UPDATED);
    } catch (error) {
        toast.add({
            severity: ERROR,
            summary: $gettext("Error saving scheme"),
            detail: (error as Error).message,
        });
    }
}

async function getCachedOptions(): Promise<
    ResourceInstanceReference[] | undefined
> {
    if (route.params.id === NEW) {
        return;
    }
    try {
        const options = textualWorkOptions.value || (await getOptions());
        return options;
    } catch (error) {
        toast.add({
            severity: ERROR,
            summary: $gettext("Error"),
            detail:
                error instanceof Error
                    ? error.message
                    : $gettext("Could not fetch options for the standard"),
        });
    }
}

async function setSchemeInstance(
    options: ResourceInstanceReference[] | undefined,
) {
    try {
        const scheme = await fetchLingoResourcePartial(
            "scheme",
            route.params.id as string,
            "creation",
        );

        const hydratedResults = options?.map((option) => {
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
    } catch (error) {
        toast.add({
            severity: ERROR,
            summary: $gettext("Error"),
            detail:
                error instanceof Error
                    ? error.message
                    : $gettext("Could not fetch the scheme standard"),
        });
    }
}

async function getSectionValue() {
    const options = await getCachedOptions();

    if (options) {
        setSchemeInstance(options);
    }
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
    <div v-if="mode === VIEW">
        <SchemeReportSection
            :title-text="$gettext('Scheme Standards Followed')"
            :button-text="$gettext('Update Scheme Standards')"
            @open-editor="emit(OPEN_EDITOR)"
        >
            <ResourceInstanceRelationships
                :value="schemeInstance?.creation?.creation_sources"
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
        <Button
            :label="$gettext('Update')"
            @click="save"
        />
    </div>
</template>
