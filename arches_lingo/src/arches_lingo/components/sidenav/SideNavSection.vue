<script setup lang="ts">
import { inject } from "vue";

import type { Ref } from "vue";
import type { SideNavMenuItem } from "@/arches_lingo/types.ts";

const navIsExpanded = inject<Ref<boolean>>("navIsExpanded");

const props = defineProps<{
    item: SideNavMenuItem;
}>();
</script>

<template>
    <div
        v-if="!props.item.route && navIsExpanded"
        class="nav-header nav-button p-button"
    >
        <i
            v-if="props.item.icon"
            :class="props.item.icon"
        ></i>
        <span>{{ props.item.label }}</span>
    </div>
    <div
        v-for="child in props.item.items"
        :key="child.key"
        class="nav-child"
        :class="child.disabled ? 'disabled' : ''"
    >
        <RouterLink
            v-if="child.route && (child.showIconIfCollapsed || navIsExpanded)"
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
                    disabled: navIsExpanded,
                }"
                :href="href"
                class="nav-button p-button"
                @click="navigate"
            >
                <i
                    v-if="child.icon"
                    :class="child.icon"
                ></i>
                <span v-if="navIsExpanded">{{ child.label }}</span>
            </a>
        </RouterLink>
    </div>
</template>

<style scoped>
.disabled {
    opacity: var(--p-disabled-opacity);
    cursor: default;
    user-select: none;
}

.nav-header {
    justify-content: flex-start;
    /* color: var(--p-slate-50); */
}
</style>
