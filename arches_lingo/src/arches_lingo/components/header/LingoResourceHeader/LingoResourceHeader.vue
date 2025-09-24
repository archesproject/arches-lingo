<script setup lang="ts">
import { inject } from "vue";

import { useConfirm } from "primevue/useconfirm";
import { useGettext } from "vue3-gettext";
import { useRouter } from "vue-router";
import { useToast } from "primevue/usetoast";

import Button from "primevue/button";
import ConfirmDialog from "primevue/confirmdialog";
import Skeleton from "primevue/skeleton";

import LingoResourceExport from "@/arches_lingo/components/header/LingoResourceHeader/components/LingoResourceExport.vue";

import type {
    ResourceHeaderData,
    ResourceInstanceResult,
} from "@/arches_lingo/types.ts";
import { deleteLingoResource } from "@/arches_lingo/api.ts";
import {
    DANGER,
    DEFAULT_ERROR_TOAST_LIFE,
    ERROR,
    SECONDARY,
} from "@/arches_lingo/constants.ts";
import { routeNames } from "@/arches_lingo/routes.ts";

const refreshSchemeHierarchy = inject<() => void>("refreshSchemeHierarchy");

const props = defineProps<{
    resource: ResourceInstanceResult;
    headerData: ResourceHeaderData;
    sectionTitle: string;
    graphSlug: string;
    nodegroupAlias: string;
    isLoading: boolean;
}>();

const toast = useToast();
const { $gettext } = useGettext();
const confirm = useConfirm();
const router = useRouter();

function confirmDelete() {
    confirm.require({
        header: $gettext("Confirmation"),
        message: $gettext(
            "Are you sure you want to delete this {SCHEME OR CONCEPT}?",
        ),
        group: "delete-resource",
        accept: () => {
            if (!props.resource) {
                return;
            }

            try {
                deleteLingoResource(
                    props.graphSlug,
                    props.resource.resourceinstanceid,
                ).then(() => {
                    const schemeIdentifier =
                        props.resource!.aliased_data?.part_of_scheme
                            ?.aliased_data.part_of_scheme?.node_value;

                    if (schemeIdentifier) {
                        router.push({
                            name: routeNames.scheme,
                            params: { id: schemeIdentifier },
                        });
                    } else {
                        router.push({
                            name: routeNames.schemes,
                        });
                    }

                    refreshSchemeHierarchy!();
                });
            } catch (error) {
                toast.add({
                    severity: ERROR,
                    life: DEFAULT_ERROR_TOAST_LIFE,
                    summary: $gettext("Error deleting resource"),
                    detail: error instanceof Error ? error.message : undefined,
                });
            }
        },
        rejectProps: {
            label: $gettext("Cancel"),
            severity: SECONDARY,
            outlined: true,
        },
        acceptProps: {
            label: $gettext("Delete"),
            severity: DANGER,
        },
    });
}
</script>

<template>
    <ConfirmDialog group="delete-resource" />

    <Skeleton
        v-if="isLoading"
        style="width: 100%"
    />
    <div
        v-else
        class="header"
    >
        <div class="header-toolbar">
            <div class="header-title">
                <h2 v-if="props.headerData?.descriptor?.name">
                    <!-- TODO: display dynamic icon for resource type -->
                    <i
                        v-if="props.headerData?.partOfScheme?.node_value"
                        class="pi pi-tag resource-icon"
                    ></i>
                    <span>{{ props.headerData?.descriptor?.name }}</span>
                    <span
                        v-if="props.headerData?.descriptor?.language"
                        class="label-lang"
                    >
                        ({{ props.headerData?.descriptor?.language }})
                    </span>
                </h2>
                <slot name="concept-controls"></slot>
            </div>
            <div class="header-buttons">
                <slot name="general-controls"></slot>
                <LingoResourceExport :resource="props.resource" />
                <!-- TODO: button should reflect published state of concept: delete if draft, deprecate if URI is present -->
                <Button
                    icon="pi pi-trash"
                    severity="danger"
                    :label="$gettext('Delete')"
                    :aria-label="$gettext('Delete {SCHEME OR CONCEPT}')"
                    @click="confirmDelete"
                />
            </div>
        </div>

        <div class="header-content">
            <div class="header-row">
                <div class="header-item">
                    <span class="header-item-label">
                        {{ $gettext("Identifier:") }}
                    </span>
                    <span v-if="props.headerData?.identifier">
                        <Button
                            v-for="value in props.headerData?.identifier"
                            :key="value"
                            :label="value"
                            class="uri-label"
                            variant="link"
                            as="a"
                            :href="value"
                            target="_blank"
                            rel="noopener"
                        ></Button>
                    </span>
                    <span
                        v-else
                        class="header-item-value"
                        >{{ $gettext("No Identifier assigned") }}</span
                    >
                </div>
                <div class="header-item">
                    <span class="header-item-label">{{
                        $gettext("URI (provisonal): ")
                    }}</span>
                    <Button
                        v-if="props.headerData?.uri"
                        :label="props.headerData?.uri"
                        class="uri-label"
                        variant="link"
                        as="a"
                        :href="props.headerData?.uri"
                        target="_blank"
                        rel="noopener"
                    ></Button>
                    <span
                        v-else
                        class="header-item-value"
                        >{{ $gettext("No URI assigned") }}</span
                    >
                </div>
            </div>
            <div class="header-row">
                <!-- Scheme / Concept specific content rendered in slot -->
                <slot name="graph-specific-content"></slot>

                <div
                    v-if="props.headerData?.partOfScheme"
                    class="concept-relationships-container"
                >
                    <span>
                        <!-- TODO: Human-reable conceptid to be displayed here -->
                        <div class="header-item">
                            <span class="header-item-label">
                                {{ $gettext("Scheme:") }}
                            </span>
                            <span class="header-item-value">
                                <RouterLink
                                    v-if="
                                        props.headerData?.partOfScheme
                                            ?.node_value
                                    "
                                    :to="`/scheme/${props.headerData?.partOfScheme?.node_value?.[0]?.resourceId}`"
                                >
                                    {{
                                        props.headerData?.partOfScheme
                                            ?.display_value
                                    }}
                                </RouterLink>
                                <span v-else>--</span>
                            </span>
                        </div>
                    </span>
                    <span>
                        <div class="header-item">
                            <span class="header-item-label">
                                {{ $gettext("Parent Concept(s):") }}
                            </span>
                            <span
                                v-if="props.headerData?.parentConcepts?.length"
                            >
                                <span
                                    v-for="parent in props.headerData
                                        ?.parentConcepts"
                                    :key="parent.details[0].resource_id"
                                    class="header-item-value parent-concept"
                                >
                                    <RouterLink
                                        :to="`/concept/${parent.details[0].resource_id}`"
                                        >{{
                                            parent.details[0].display_value
                                        }}</RouterLink
                                    >
                                </span>
                            </span>
                            <span v-else>--</span>
                        </div>
                    </span>
                </div>

                <!-- TODO: Life Cycle mgmt functionality goes here -->
                <div class="lifecycle-container">
                    <div class="header-item">
                        <span class="header-item-label">
                            {{ $gettext("Life cycle state:") }}
                        </span>
                        <span class="header-item-value">
                            {{ props.headerData?.lifeCycleState }}
                        </span>
                    </div>
                    <div class="header-item">
                        <span class="header-item-label">
                            {{ $gettext("Owner:") }}
                        </span>
                        <span class="header-item-value">
                            {{
                                props.headerData?.principalUser ||
                                $gettext("Anonymous")
                            }}
                        </span>
                    </div>
                </div>
            </div>
        </div>
    </div>
</template>

<style scoped>
h2 {
    margin-top: 0;
    margin-bottom: 0;
    font-size: var(--p-lingo-font-size-large);
    font-weight: var(--p-lingo-font-weight-normal);
}

.header {
    background: var(--p-header-background);
    border-bottom: 0.0625rem solid var(--p-header-toolbar-border);
}

.header-toolbar {
    min-height: 3rem;
    align-items: center;
    display: flex;
    justify-content: space-between;
    background: var(--p-header-toolbar-background);
    border-bottom: 0.0625rem solid var(--p-header-toolbar-border);
    padding: 0.5rem 1rem;
}

.header-title {
    display: flex;
    align-items: center;
    gap: 1rem;
}

.resource-icon {
    padding-inline-end: 0.25rem;
}

.header-content {
    padding: 0.5rem 1rem 1rem 1.5rem;
}

.header-row {
    display: flex;
    justify-content: space-between;
    align-items: center;
}

.header-item {
    display: inline-flex;
    align-items: baseline;
}

.header-item-label {
    font-weight: var(--p-lingo-font-weight-normal);
    font-size: var(--p-lingo-font-size-smallnormal);
    color: var(--p-header-item-label);
    margin-inline-end: 0.25rem;
}

.header-item-value {
    font-size: var(--p-lingo-font-size-smallnormal);
    color: var(--p-primary-500);
}

.header-buttons {
    display: flex;
    gap: 0.25rem;
}

.label-lang {
    font-size: var(--p-lingo-font-size-smallnormal);
    color: var(--p-text-muted-color);
    vertical-align: baseline;
}

.concept-relationships-container {
    display: flex;
    flex-direction: column;
}

.lifecycle-container {
    display: flex;
    flex-direction: column;
    align-items: end;
}

.uri-label {
    font-size: var(--p-lingo-font-size-small);
    font-weight: var(--p-lingo-font-weight-normal);
    color: var(--p-primary-500);
}

.parent-concept {
    margin-inline-end: 0.5rem;
}

.parent-concept:hover a {
    color: var(--p-primary-700);
}

.p-button-link {
    padding: 0;
    margin: 0;
}

:deep(a) {
    font-size: var(--p-lingo-font-size-smallnormal);
    color: var(--p-primary-500);
}
</style>
