<script setup lang="ts">
import arches from "arches";
import { useGettext } from "vue3-gettext";

import Button from "primevue/button";

import { SECONDARY } from "@/arches_lingo/constants.ts";

const { $gettext } = useGettext();
</script>

<template>
    <div style="display: flex; justify-content: space-between; width: 30%">
        <Button
            as="a"
            :label="$gettext('Register')"
            :href="arches.urls.signup"
            :severity="SECONDARY"
            :outlined="true"
        />
        <Button
            as="a"
            :label="$gettext('Multi-factor login')"
            :href="arches.urls.auth + '?next=/'"
            :severity="SECONDARY"
            :outlined="true"
        />
    </div>
</template>
