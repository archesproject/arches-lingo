<script setup lang="ts">
import { inject, ref } from "vue";
import { useGettext } from "vue3-gettext";
import { systemLanguageKey, NEW } from "@/arches_lingo/constants.ts";
import { routeNames } from "@/arches_lingo/routes.ts";

import Card from "primevue/card";
import Menubar from "primevue/menubar";

import { extractDescriptors } from "@/arches_lingo/utils.ts";

import type { Language } from "@/arches_component_lab/types";
import type { ResourceInstanceResult } from "@/arches_lingo/types";

const { $gettext } = useGettext();
const systemLanguage = inject(systemLanguageKey) as Language;

const { scheme } = defineProps<{ scheme: ResourceInstanceResult }>();
const schemeURL = {
    name: routeNames.scheme,
    params: { id: scheme.resourceinstanceid },
};

const schemeDescriptor = extractDescriptors(scheme, systemLanguage);

const items = ref([
    {
        label: $gettext("Manage"),
        icon: "pi pi-cog",
        items: [
            {
                label: $gettext("Settings"),
                description: $gettext("Manage scheme metadata"),
                route: "/theming/styled",
            },
            {
                label: $gettext("Edit Scheme"),
                description: $gettext("Create edit version and lock scheme"),
                route: "/theming/unstyled",
            },
            {
                label: $gettext("Copy Scheme"),
                description: $gettext("Copy to a new scheme"),
                route: "/theming/unstyled",
            },
            {
                label: $gettext("Delete Unpublished Scheme"),
                description: $gettext("Permanently remove scheme"),
                route: "/theming/unstyled",
            },
            {
                label: $gettext("Publish Scheme"),
                description: $gettext("Make scheme available for access"),
                route: "/theming/unstyled",
            },
            {
                label: $gettext("Save Edited Scheme"),
                description: $gettext("Make scheme available for access"),
                route: "/theming/unstyled",
            },
            {
                label: $gettext("Deprecate Published Scheme"),
                description: $gettext("Prohibit editing a published scheme"),
                route: "/theming/unstyled",
            },
            {
                label: "Un-deprecate Scheme",
                description: $gettext("Revive a deprecated scheme"),
                route: "/theming/unstyled",
            },
            {
                label: $gettext("View Scheme Statistics"),
                description: $gettext("Summary of scheme content"),
                route: "/theming/unstyled",
            },
        ],
    },
]);
</script>

<template>
    <Card>
        <template #title>
            <RouterLink :to="schemeURL">
                <div v-if="scheme.resourceinstanceid === NEW">
                    {{ $gettext("New Scheme") }}
                </div>
                <div
                    v-else
                    class="scheme-card-header"
                >
                    {{ schemeDescriptor.name }}
                </div>
            </RouterLink>
        </template>
        <template #content>
            <RouterLink
                class="containing-link"
                :to="schemeURL"
            >
                <div v-if="scheme.resourceinstanceid === NEW">
                    <div class="scheme-circle">
                        <i class="pi pi-share-alt new-scheme-icon"></i>
                    </div>
                </div>
                <span class="scheme-card-description">{{
                    schemeDescriptor.description
                }}</span>
            </RouterLink>
        </template>
        <template #footer>
            <div
                v-if="scheme.resourceinstanceid === NEW"
                style="display: flex; width: 100%"
            >
                <div class="footer-component">
                    {{
                        $gettext(
                            "Add a new thesaurus, manage concept hierarchies",
                        )
                    }}
                </div>
            </div>
            <div
                v-else
                style="display: flex; width: 100%"
            >
                <Menubar :model="items">
                    <template #start>{{ $gettext("Status") }}</template>
                    <template #item="{ item, props, hasSubmenu }">
                        <RouterLink
                            v-if="item.route"
                            v-slot="{ href, navigate }"
                            :to="item.route"
                            custom
                        >
                            <a
                                v-ripple
                                :href="href"
                                v-bind="props.action"
                                style="
                                    flex-direction: column;
                                    align-items: start;
                                "
                                @click.stop="navigate"
                            >
                                <div class="label">
                                    <span :class="item.icon" /> {{ item.label }}
                                </div>
                                <div class="description">
                                    {{ item.description }}
                                </div>
                            </a>
                        </RouterLink>
                        <a
                            v-else
                            v-ripple
                            :href="item.url"
                            :target="item.target"
                            v-bind="props.action"
                        >
                            <span :class="item.icon" />
                            <span>{{ item.label }}</span>
                            <span
                                v-if="hasSubmenu"
                                class="pi pi-fw pi-angle-down"
                            />
                        </a>
                    </template>
                </Menubar>
            </div>
        </template>
    </Card>
</template>

<style scoped>
a {
    text-decoration: none;
}

.p-card {
    width: 20rem;
    height: 20rem;
    margin: 0.25rem;
    border-radius: 0.125rem;
    overflow: auto;
}

.scheme-card-header {
    color: var(--p-scheme-card-header-color);
}

.scheme-card-description {
    color: var(--p-scheme-card-header-color);
}

:deep(.p-card-content) {
    padding: 0;
}

:deep(.p-card-content a) {
    display: block;
    height: 100%;
    padding: 1rem;
}

:deep(.scheme-card-header) {
    padding: 1rem;
}

:deep(.p-card-content) {
    overflow: hidden;
    text-overflow: ellipsis;
    flex: 1;
}

:deep(.p-card-body > .p-card-footer) {
    padding: 0;
    display: flex;
}

:deep(.p-card-footer) {
    padding: 1rem;
    border: 1px solid var(--p-button-secondary-active-border-color);
    height: 3.5rem;
}

:deep(.p-card-footer > div > div) {
    background-color: var(--p-very-light-gray);
}

:deep(.p-card-content > span),
:deep(.p-card-footer > span) {
    font-size: var(--p-lingo-font-size-xsmall);
}

.scheme-circle {
    display: inline-block;
    text-align: center;
    padding: 1.25rem;
    margin: 1rem;
    border-radius: 50%;
    background: var(--p-surface-400);
    border: 0.06rem solid var(--p-surface-900);
}

.p-menubar.p-component {
    width: 100%;
    display: flex;
    padding: 0;
    border-radius: 0;
}

:deep(.p-menubar-root-list) {
    flex: 1;
}

:deep(.p-menubar-start) {
    flex: 1;
    justify-content: center;
}

.new-scheme-icon {
    font-size: var(--p-lingo-font-size-xxlarge);
}

:deep(.p-menubar-item-link .description) {
    font-size: var(--p-lingo-font-size-xxsmall);
}

:deep(.p-menubar-item) {
    width: 100%;
    border-radius: 0;
}

:deep(.p-menubar-item.p-menubar-item-active > .p-menubar-item-content),
:deep(.p-menubar-root-list > .p-menubar-item > .p-menubar-item-content),
:deep(.p-menubar-submenu) {
    border-radius: 0;
}

:deep(.p-menubar-item-link .label) {
    font-size: var(--p-lingo-font-size-normal);
    color: var(--p-scheme-card-header-color);
}

:deep(.p-card-body) {
    display: flex;
    flex-direction: column;
    padding: 0;
    flex-grow: 1;
    text-align: center;
    overflow: hidden;
    gap: 0;
}

.footer-component {
    display: flex;
    align-items: center;
    justify-content: center;
}

:deep(.p-card-content) {
    overflow: auto;
}
</style>
