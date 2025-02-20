<script setup lang="ts">
import { computed, ref, useTemplateRef } from "vue";

import { useGettext } from "vue3-gettext";
import { useRoute } from "vue-router";

import { Form } from "@primevue/forms";
import Button from "primevue/button";

import NonLocalizedStringWidget from "@/arches_component_lab/widgets/NonLocalizedStringWidget/NonLocalizedStringWidget.vue";
import ReferenceSelectWidget from "@/arches_controlled_lists/widgets/ReferenceSelectWidget/ReferenceSelectWidget.vue";
import ResourceInstanceMultiSelectWidget from "@/arches_component_lab/widgets/ResourceInstanceMultiSelectWidget/ResourceInstanceMultiSelectWidget.vue";
import DateWidget from "@/arches_component_lab/widgets/DateWidget/DateWidget.vue";

import { upsertLingoTile } from "@/arches_lingo/api.ts";

import { EDIT } from "@/arches_lingo/constants.ts";

import { checkDeepEquality } from "@/arches_lingo/utils.ts";

import type { FormSubmitEvent } from "@primevue/forms";
import type { AppellativeStatus } from "@/arches_lingo/types.ts";

const props = withDefaults(
    defineProps<{
        value?: AppellativeStatus;
    }>(),
    {
        value: () => ({}) as AppellativeStatus,
    },
);

// this is to compensate for the of a Form type in the primevue/forms module
interface FormInstance {
    fields: Record<
        string,
        {
            options: { name: string };
            states: { value: unknown };
        }
    >;
}

const route = useRoute();
const { $gettext } = useGettext();

const formRef = useTemplateRef<FormInstance>("formRef");
const formKey = ref(0);

const isFormDirty = computed(() => {
    if (!formRef.value) return false;

    return Object.values(formRef.value.fields).some((fieldData) => {
        return !checkDeepEquality(
            props.value[fieldData.options.name as keyof AppellativeStatus],
            fieldData.states.value,
        );
    });
});

async function save(e: FormSubmitEvent) {
    upsertLingoTile(
        "scheme",
        "appellative_status",
        {
            resourceinstance: route.params.id as string,
            ...Object.entries(e.states).reduce(
                (acc, [key, state]) => {
                    acc[key] = state.value;
                    return acc;
                },
                {} as Record<string, unknown>,
            ),
            tileid: props.value.tileid,
        },
        props.value.tileid,
    );
}

function reset() {
    formKey.value += 1;
}
</script>

<template>
    <Form
        v-if="Object.values(props.value).length"
        ref="formRef"
        :key="formKey"
        @submit="save"
        @reset="reset"
    >
        <NonLocalizedStringWidget
            graph-slug="scheme"
            node-alias="appellative_status_ascribed_name_content"
            :initial-value="
                props.value.appellative_status_ascribed_name_content
            "
            :mode="EDIT"
        />
        <DateWidget
            graph-slug="scheme"
            node-alias="appellative_status_timespan_begin_of_the_begin"
            :initial-value="
                props.value.appellative_status_timespan_begin_of_the_begin
            "
            :mode="EDIT"
        />
        <DateWidget
            graph-slug="scheme"
            node-alias="appellative_status_timespan_end_of_the_end"
            :initial-value="
                props.value.appellative_status_timespan_end_of_the_end
            "
            :mode="EDIT"
        />

        <ResourceInstanceMultiSelectWidget
            graph-slug="scheme"
            node-alias="appellative_status_data_assignment_actor"
            :initial-value="
                props.value.appellative_status_data_assignment_actor
            "
            :mode="EDIT"
        />
        <ResourceInstanceMultiSelectWidget
            graph-slug="scheme"
            node-alias="appellative_status_data_assignment_object_used"
            :initial-value="
                props.value.appellative_status_data_assignment_object_used
            "
            :mode="EDIT"
        />

        <ReferenceSelectWidget
            graph-slug="scheme"
            node-alias="appellative_status_ascribed_name_language"
            :initial-value="
                props.value.appellative_status_ascribed_name_language
            "
            :mode="EDIT"
        />
        <ReferenceSelectWidget
            graph-slug="scheme"
            node-alias="appellative_status_ascribed_relation"
            :initial-value="props.value.appellative_status_ascribed_relation"
            :mode="EDIT"
        />
        <ReferenceSelectWidget
            graph-slug="scheme"
            node-alias="appellative_status_status"
            :initial-value="props.value.appellative_status_status"
            :mode="EDIT"
        />
        <ReferenceSelectWidget
            graph-slug="scheme"
            node-alias="appellative_status_status_metatype"
            :initial-value="props.value.appellative_status_status_metatype"
            :mode="EDIT"
        />
        <ReferenceSelectWidget
            graph-slug="scheme"
            node-alias="appellative_status_data_assignment_type"
            :initial-value="props.value.appellative_status_data_assignment_type"
            :mode="EDIT"
        />

        <div style="display: flex">
            <Button
                :label="$gettext('Update')"
                type="submit"
                :disabled="!isFormDirty"
            />
            <Button
                :label="$gettext('Reset')"
                type="reset"
                :disabled="!isFormDirty"
            />
        </div>
    </Form>
</template>
