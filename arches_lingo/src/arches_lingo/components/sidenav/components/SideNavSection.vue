<script setup lang="ts">
import { inject } from "vue";

import type { MenuItem } from "primevue/menuitem";
import type { SideNavMenuItem } from "@/arches_lingo/types.ts";

const props = defineProps<{
    item: SideNavMenuItem;
}>();

const isNavExpanded = inject("isNavExpanded", false);

function getChildLabel(child: MenuItem): string | undefined {
    return typeof child.label === "function" ? child.label() : child.label;
}
</script>

<template>
    <div
        v-if="!props.item.route && isNavExpanded"
        class="nav-header nav-button p-button"
    >
        <i
            v-if="props.item.icon"
            :class="props.item.icon"
        ></i>
        <span style="white-space: nowrap; flex-shrink: 0">{{
            props.item.label
        }}</span>
    </div>
    <div
        v-for="child in props.item.items"
        :key="child.key"
        class="nav-child"
    >
        <RouterLink
            v-if="child.route && (child.showIconIfCollapsed || isNavExpanded)"
            v-slot="{ href, navigate }"
            :to="child.route"
            custom
        >
            <a
                v-tooltip="{
                    value: child.label,
                    pt: {
                        text: {
                            style: { fontFamily: 'var(--p-lingo-font-family)' },
                        },
                    },
                    disabled: isNavExpanded,
                }"
                :href="href"
                :aria-label="isNavExpanded ? undefined : getChildLabel(child)"
                :style="{
                    paddingInlineStart: isNavExpanded ? '2rem' : '0.75rem',
                }"
                class="nav-button p-button"
                :class="child.disabled ? 'disabled' : ''"
                @click.prevent="navigate()"
            >
                <i
                    v-if="child.icon"
                    :class="child.icon"
                    aria-hidden="true"
                ></i>
                <span
                    v-if="isNavExpanded"
                    style="white-space: nowrap; flex-shrink: 0"
                >
                    {{ child.label }}
                </span>
            </a>
        </RouterLink>
        <a
            v-else-if="
                child.url && (child.showIconIfCollapsed || isNavExpanded)
            "
            v-tooltip="{
                value: child.label,
                pt: {
                    text: {
                        style: { fontFamily: 'var(--p-lingo-font-family)' },
                    },
                },
                disabled: isNavExpanded,
            }"
            :href="child.url"
            :aria-label="isNavExpanded ? undefined : getChildLabel(child)"
            :style="{
                paddingInlineStart: isNavExpanded ? '2rem' : '0.75rem',
            }"
            class="nav-button p-button"
            :class="child.disabled ? 'disabled' : ''"
        >
            <i
                v-if="child.icon"
                :class="child.icon"
                aria-hidden="true"
            ></i>
            <span
                v-if="isNavExpanded"
                style="white-space: nowrap; flex-shrink: 0"
            >
                {{ child.label }}
            </span>
        </a>
    </div>
</template>

<style scoped>
.nav-child {
    background-color: var(--p-primary-950);
    cursor: pointer;
}
.disabled {
    opacity: var(--p-disabled-opacity);
    cursor: default;
    user-select: none;
    cursor: not-allowed;
}
.disabled:hover {
    background-color: var(--p-disabled-opacity);
}

.p-button {
    justify-content: flex-start;
    border: 0 !important;
}
</style>
