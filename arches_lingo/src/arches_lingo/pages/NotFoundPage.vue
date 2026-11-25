<script setup lang="ts">
import { computed } from "vue";
import { RouterLink, useRoute, useRouter } from "vue-router";
import { useGettext } from "vue3-gettext";

import Button from "primevue/button";

import { routeNames } from "@/arches_lingo/routes.ts";
import {
    CONCEPT_ROUTE_NAMES,
    SCHEME_ROUTE_NAMES,
} from "@/arches_lingo/utils.ts";

const { $gettext } = useGettext();
const route = useRoute();
const router = useRouter();

// The not-found route keeps the URL the user followed, so resolving that URL
// again gives the route it was meant for: a concept, a scheme, or nothing.
const intendedRouteName = computed(() =>
    String(router.resolve(route.fullPath).name ?? ""),
);

const notFoundHeading = computed(() => {
    if (CONCEPT_ROUTE_NAMES.has(intendedRouteName.value)) {
        return $gettext("Concept not found");
    }
    if (SCHEME_ROUTE_NAMES.has(intendedRouteName.value)) {
        return $gettext("Scheme not found");
    }
    return $gettext("Page not found");
});

const notFoundDescription = computed(() => {
    if (CONCEPT_ROUTE_NAMES.has(intendedRouteName.value)) {
        return $gettext(
            "No concept matches %{path}. It may have been deleted, or the address may be mistyped.",
            { path: route.path },
            true,
        );
    }
    if (SCHEME_ROUTE_NAMES.has(intendedRouteName.value)) {
        return $gettext(
            "No scheme matches %{path}. It may have been deleted, or the address may be mistyped.",
            { path: route.path },
            true,
        );
    }
    return $gettext(
        "Nothing in Lingo matches %{path}. It may have been deleted, or the address may be mistyped.",
        { path: route.path },
        true,
    );
});
</script>

<template>
    <div class="not-found-page">
        <h1 class="page-title">{{ notFoundHeading }}</h1>
        <p class="page-description">{{ notFoundDescription }}</p>
        <div class="not-found-actions">
            <Button
                :as="RouterLink"
                :to="{ name: routeNames.schemes }"
                :label="$gettext('Browse schemes')"
                icon="pi pi-lightbulb"
                class="not-found-action"
            />
            <Button
                :as="RouterLink"
                :to="{ name: routeNames.dashboard }"
                :label="$gettext('Go to the dashboard')"
                icon="pi pi-home"
                severity="secondary"
                variant="outlined"
                class="not-found-action"
            />
        </div>
    </div>
</template>

<style scoped>
.not-found-page {
    height: 100%;
    overflow-y: auto;
    padding: 2rem;
    font-family: var(--p-lingo-font-family);
}

.page-title {
    margin: 0;
    font-size: 1.5rem;
    font-weight: var(--p-lingo-font-weight-normal);
    color: var(--p-text-color);
}

.page-description {
    margin: 0.5rem 0 1.5rem;
    max-width: 40rem;
    color: var(--p-text-color);
    overflow-wrap: anywhere;
}

.not-found-actions {
    display: flex;
    flex-wrap: wrap;
    gap: 0.75rem;
}

.not-found-action {
    text-decoration: none;
}
</style>
