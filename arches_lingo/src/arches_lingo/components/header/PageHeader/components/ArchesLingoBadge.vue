<script setup lang="ts">
import { useGettext } from "vue3-gettext";

import { routeNames } from "@/arches_lingo/routes.ts";

import { generateArchesURL } from "@/arches/utils/generate-arches-url.ts";

const props = withDefaults(
    defineProps<{
        isLink?: boolean;
    }>(),
    {
        isLink: true,
    },
);

const { $gettext } = useGettext();
</script>

<template>
    <!-- We could break this into subcomponents to DRY it up, but it's small enough IMO -->
    <div>
        <RouterLink
            v-if="props.isLink"
            :to="{ name: routeNames.root }"
            style="text-decoration: none; color: inherit"
        >
            <div class="lingo-badge">
                <img
                    :src="
                        generateArchesURL('static_url') +
                        'img/arches_logo_light.png'
                    "
                    alt="Arches Logo"
                    style="height: 1.5rem; width: auto"
                />
                <h1 class="lingo-title">{{ $gettext("Lingo") }}</h1>
            </div>
        </RouterLink>
        <div
            v-else
            class="lingo-badge"
        >
            <img
                :src="
                    generateArchesURL('static_url') +
                    'img/arches_logo_light.png'
                "
                alt="Arches Logo"
                style="height: 1.5rem; width: auto"
            />
            <h1 class="lingo-title">{{ $gettext("Lingo") }}</h1>
        </div>
    </div>
</template>

<style scoped>
.lingo-badge {
    display: flex;
    align-items: center;
}

.lingo-title {
    font-weight: var(--p-lingo-font-weight-normal);
    font-size: var(--p-lingo-font-size-large);
    margin: 0rem;
    margin-inline-start: 0.5rem;
}
</style>
