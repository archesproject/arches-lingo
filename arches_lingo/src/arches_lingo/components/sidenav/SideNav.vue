<script setup lang="ts">
import { ref } from "vue";
import { useGettext } from "vue3-gettext";

import { routeNames } from "@/arches_lingo/routes.ts";

const { $gettext } = useGettext();

const items = ref([
    {
        icon: "fa fa-home",
        routeName: routeNames.root,
        linkName: $gettext("Home"),
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
}

.p-button {
    min-height: var(--p-button-lg-icon-only-width);
    min-width: var(--p-button-lg-icon-only-width);
    border-radius: 0;
    font-size: var(--p-lingo-font-size-large);
    border-bottom: 0.1rem solid var(--p-button-outlined-primary-border-color);
}

@media screen and (max-width: 960px) {
    .sidenav {
        display: none;
    }
}
</style>
