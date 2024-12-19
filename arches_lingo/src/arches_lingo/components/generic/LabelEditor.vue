<script setup lang="ts">
import { defineProps, ref } from "vue";

import NonLocalizedString from "@/arches_lingo/components/generic/NonLocalizedString.vue";

// import ResourceInstanceRelationships from "@/arches_lingo/components/generic/ResourceInstanceRelationships.vue";

import { EDIT } from "@/arches_lingo/constants.ts";

import type { AppellativeStatus } from "@/arches_lingo/types.ts";

const props = withDefaults(
    defineProps<{
        value?: AppellativeStatus;
    }>(),
    {
        value: () => ({}) as AppellativeStatus,
    },
);

const appellative_status = ref(props.value);

function onUpdate(newValue: string) {
    // handle the update
    console.log("Update new value here!" + newValue);
}
</script>

<template>
    <!-- Label: string -->
    <label for="">{{ $gettext("Label") }}</label>
    <NonLocalizedString
        :value="
            appellative_status?.appellative_status_ascribed_name_content ?? ''
        "
        :mode="EDIT"
        @update="onUpdate"
    />
    <!-- Label Language: reference datatype -->
    <label for="">{{ $gettext("Label Language") }}</label>

    <!-- Label Type: reference datatype -->
    <label for="">{{ $gettext("Label Type") }}</label>

    <!-- Label Status: reference datatype -->
    <label for="">{{ $gettext("Label Status") }}</label>

    <!-- Label Status Metatype: reference datatype -->
    <label for="">{{ $gettext("Label Metatype") }}</label>

    <!-- Label Temporal Validity Start: date -->
    <label for="">{{ $gettext("Label Temporal Validity Start") }}</label>

    <!-- Label Temporal Validity End: date -->
    <label for="">{{ $gettext("Label Temporal Validity End") }}</label>

    <!-- Contributor: resource instance -->
    <label for="">{{ $gettext("Contributor") }}</label>

    <!-- Sources: resource instance -->
    <label for="">{{ $gettext("Sources") }}</label>

    <!-- Warrant Type: reference datatype -->
    <label for="">{{ $gettext("Warrant Type") }}</label>
</template>
