<script setup lang="ts">
import { ref } from "vue";
import { useGettext } from "vue3-gettext";

import { routeNames } from "@/arches_lingo/routes.ts";

const { $gettext } = useGettext();

const items = ref([
    {
        icon: "pi pi-home",
        routeName: routeNames.root,
        linkName: $gettext("Home"),
    },
    {
        icon: "pi pi-search",
        routeName: routeNames.advancedSearch,
        linkName: $gettext("Advanced Search"),
    },
]);
</script>

<template>
    <aside class="sidenav">
        <div
            v-for="item in items"
            :key="item.routeName"
        >
            <RouterLink
                v-tooltip="{
                    value: item.linkName,
                    pt: { text: { style: { fontFamily: 'sans-serif' } } },
                }"
                :to="{ name: item.routeName }"
                class="p-button p-component p-button-primary"
                style="text-decoration: none"
            >
                <i
                    :class="item.icon"
                    aria-hidden="true"
                ></i>
            </RouterLink>
        </div>
    </aside>
</template>

<style scoped>
.sidenav {
    display: flex;
    flex-direction: column;
    align-items: center;
    border-right: 1px solid var(--p-menubar-border-color);
    background: var(--p-primary-950);
    width: 3.125rem;
}

.p-button {
    height: 2.5rem;
    font-size: var(--p-lingo-font-size-large);
    background: var(--p-primary-950) !important;
    border: none !important;
    border-radius: 0;
}

i {
    color: var(--p-surface-0);
}

.p-button:hover {
    background: var(--p-button-primary-hover-background) !important;
}

@media screen and (max-width: 960px) {
    .sidenav {
        display: none;
    }
}
</style>
