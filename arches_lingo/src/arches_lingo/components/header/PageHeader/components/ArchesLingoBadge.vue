<script setup lang="ts">
import { useRouter, RouterLink } from "vue-router";
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
const router = useRouter();

// This is to force a reload of the page when the badge is clicked
// when the current route is the root route. `navigate` only prevents the
// default (and navigates) for plain left clicks, so modified clicks such as
// ctrl/cmd+click still open the link natively.
function handleClick(
    event: MouseEvent,
    navigate: (event?: MouseEvent) => unknown,
    isActive: boolean,
) {
    navigate(event);

    if (isActive && event.defaultPrevented) {
        router.go(0);
    }
}
</script>

<template>
    <!-- We could break this into subcomponents to DRY it up, but it's small enough IMO -->
    <div>
        <RouterLink
            v-if="props.isLink"
            v-slot="{ href, navigate, isActive }"
            :to="{ name: routeNames.root }"
            :custom="true"
        >
            <a
                :href="href"
                class="lingo-badge lingo-badge-link"
                @click="handleClick($event, navigate, isActive)"
            >
                <img
                    :src="
                        generateArchesURL('arches_lingo:static_url') +
                        'img/arches_logo_light.png'
                    "
                    alt="Arches Logo"
                    style="height: 1.5rem; width: auto"
                />
                <h1 class="lingo-title">{{ $gettext("Lingo") }}</h1>
            </a>
        </RouterLink>
        <div
            v-else
            class="lingo-badge"
        >
            <img
                :src="
                    generateArchesURL('arches_lingo:static_url') +
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
    cursor: pointer;
}

.lingo-badge-link {
    color: inherit;
    text-decoration: none;
}

.lingo-title {
    font-weight: var(--p-lingo-font-weight-normal);
    font-size: var(--p-lingo-font-size-large);
    margin: 0rem;
    margin-inline-start: 0.5rem;
}
</style>
