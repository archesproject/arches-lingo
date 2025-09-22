<script setup lang="ts">
import { inject, onMounted, ref } from "vue";
import { useGettext } from "vue3-gettext";

import { useToast } from "primevue/usetoast";

import Button from "primevue/button";
import LingoResourceHeader from "@/arches_lingo/components/header/LingoResourceHeader/LingoResourceHeader.vue";

import {
    DEFAULT_ERROR_TOAST_LIFE,
    ERROR,
    systemLanguageKey,
} from "@/arches_lingo/constants.ts";

import { fetchLingoResource } from "@/arches_lingo/api.ts";
import { extractDescriptors } from "@/arches_lingo/utils.ts";

import type {
    DataComponentMode,
    IdentifierAliases,
    ResourceInstanceResult,
    ResourceHeaderData,
} from "@/arches_lingo/types.ts";
import type { Language } from "@/arches_component_lab/types.ts";

const props = defineProps<{
    mode: DataComponentMode;
    sectionTitle: string;
    componentName: string;
    graphSlug: string;
    resourceInstanceId: string | undefined;
    nodegroupAlias: string;
}>();

const toast = useToast();
const { $gettext } = useGettext();
const systemLanguage = inject(systemLanguageKey) as Language;

const scheme = ref<ResourceInstanceResult>();
const data = ref<ResourceHeaderData>();
const isLoading = ref(true);

function extractSchemeHeaderData(scheme: ResourceInstanceResult) {
    const name = scheme?.name;
    const descriptor = extractDescriptors(scheme, systemLanguage);
    // TODO: get human-readable user name from resource endpoint
    const principalUser = "Anonymous"; //scheme?.principalUser; // returns userid int
    // TODO: get human-readable life cycle state from resource endpoint
    const lifeCycleState = $gettext("Draft");
    const identifier = scheme?.aliased_data?.identifier.map(
        (value: IdentifierAliases) => {
            return value.aliased_data?.identifier_content?.node_value;
        },
    );

    data.value = {
        name: name,
        descriptor: descriptor,
        principalUser: principalUser,
        lifeCycleState: lifeCycleState,
        identifier: identifier,
    };
}

onMounted(async () => {
    try {
        if (!props.resourceInstanceId) {
            return;
        }

        scheme.value = await fetchLingoResource(
            props.graphSlug,
            props.resourceInstanceId,
        );

        extractSchemeHeaderData(scheme.value!);
    } catch (error) {
        toast.add({
            severity: ERROR,
            life: DEFAULT_ERROR_TOAST_LIFE,
            summary: $gettext("Unable to fetch scheme"),
            detail: error instanceof Error ? error.message : undefined,
        });
    } finally {
        isLoading.value = false;
    }
});
</script>

<template>
    <LingoResourceHeader
        v-if="scheme && data"
        :resource="scheme"
        :header-data="data"
        :section-title="props.sectionTitle"
        :graph-slug="props.graphSlug"
        :nodegroup-alias="props.nodegroupAlias"
        :is-loading="isLoading"
    >
        <template #controls>
            <Button
                icon="pi pi-plus-circle"
                :label="$gettext('Add Top Concept')"
                class="add-button"
            ></Button>
            <!-- TODO: button should allow user to publish scheme if draft, retire scheme if published -->
            <Button
                icon="pi pi-book"
                :label="$gettext('Publish')"
                class="add-button"
            ></Button>
        </template>

        <template #graph-specific-content>
            <div class="header-row metadata-container">
                <!-- TODO: Load Scheme languages here -->
                <div class="language-chip-container">
                    <span class="scheme-language">
                        {{ $gettext("English (en)") }}
                    </span>
                    <span class="scheme-language">
                        {{ $gettext("German (de)") }}
                    </span>
                    <span class="scheme-language">
                        {{ $gettext("French (fr)") }}
                    </span>
                    <span class="add-language">
                        {{ $gettext("Add Language") }}
                    </span>
                </div>
            </div>
        </template>
    </LingoResourceHeader>
</template>

<style scoped>
.metadata-container {
    gap: 0.25rem;
    margin-top: 0;
    justify-content: space-between;
    align-items: center;
}

.language-chip-container {
    display: flex;
    gap: 0.25rem;
    align-items: center;
}

.scheme-language {
    padding: 0.5rem 1rem;
    background: var(--p-menubar-item-icon-color);
    border: 0.0625rem solid var(--p-menubar-item-icon-color);
    border-radius: 0.125rem;
    font-size: var(--p-lingo-font-size-smallnormal);
    color: var(--p-content-color);
}

.add-language:hover {
    cursor: pointer;
}

.add-language {
    font-size: var(--p-lingo-font-size-smallnormal);
    color: var(--p-primary-500);
    text-decoration: underline;
    padding: 0 0.5rem;
}
</style>
