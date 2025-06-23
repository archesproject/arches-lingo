<script setup lang="ts">
import { inject } from "vue";

import type { Component, Ref } from "vue";
import type { MenuItem } from "primevue/menuitem";

import Button from "primevue/button";

const expandedKeys = inject<Ref<Record<string, boolean>>>("expandedKeys");
const isExpanded = inject<Ref<boolean>>("isExpanded");
const toggleNode = inject<(item: MenuItem) => void>("toggleNode");

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

function toggleSection() {
    if (props.item.items && props.item.items.length > 0) {
        toggleNode?.(props.item);
    }
}
</script>

<template>
    <Button
        v-if="!props.item.route"
        class="nav-button"
        @click="toggleSection"
    >
        <i :class="props.item.icon"></i>
        <span v-if="isExpanded">{{ props.item.label }}</span>
        <span
            v-if="props.item.items"
            :class="
                expandedKeys?.[props.item.key]
                    ? 'pi pi-angle-up'
                    : 'pi pi-angle-down'
            "
        />
    </Button>
    <div
        v-for="child in props.item.items"
        :key="child.key"
        class="nav-children"
    >
        <RouterLink
            v-if="child.route"
            v-slot="{ href, navigate }"
            :to="child.route"
            custom
        >
            <a
                v-tooltip="{
                    value: child.label,
                    pt: {
                        text: {
                            style: { fontFamily: '--p-lingo-font-family' },
                        },
                    },
                }"
                :href="href"
                class="nav-button p-button"
                @click="navigate"
            >
                <i :class="child.icon"></i>
                <span v-if="isExpanded">{{ child.label }}</span>
            </a>
        </RouterLink>
    </div>
</template>
