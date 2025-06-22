<script setup lang="ts">
// import { inject } from "vue";

import type { Component } from "vue";

import type { MenuItem } from "primevue/menuitem";

// const isExpanded = inject("isExpanded");

const props = defineProps<{
    item: {
        component: Component;
        key: string;
        label?: string;
        icon?: string;
        route?: string;
        items?: MenuItem[];
    };
}>();
</script>

<template>
    Hello World!
    {{ props.item.key }}
    <!-- <router-link
        v-if="item.route"
        v-slot="{ href, navigate }"
        :to="item.route"
        custom
    >
        <a
            v-tooltip="{
                value: item.label,
                pt: { text: { style: { fontFamily: '-' } } },
            }"
            :href="href"
            class="nav-button p-button"
            @click="navigate"
        >
            <i :class="item.icon"></i>
            <span v-if="isExpanded">{{ item.label }}</span>
        </a>
    </router-link>
    <a
        v-else
        class="nav-button p-button"
    >
        <i :class="item.icon"></i>
        <span v-if="isExpanded">{{ item.label }}</span>
        <span
            v-if="item.items"
            class="pi pi-angle-down text-primary ml-auto"
        />
    </a> -->
</template>
