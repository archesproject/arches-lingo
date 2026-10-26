<script setup lang="ts">
import { inject, useId } from "vue";

import type { MenuItem } from "primevue/menuitem";
import type { SideNavMenuItem } from "@/arches_lingo/types.ts";

const props = defineProps<{
    item: SideNavMenuItem;
}>();

const isNavExpanded = inject("isNavExpanded", false);
const headingId = useId();

function getChildLabel(child: MenuItem): string | undefined {
    return typeof child.label === "function" ? child.label() : child.label;
}
</script>

<template>
    <div class="nav-section">
        <h2
            :id="headingId"
            :class="
                isNavExpanded
                    ? 'nav-header nav-button p-button'
                    : 'p-hidden-accessible'
            "
        >
            <i
                v-if="props.item.icon"
                :class="props.item.icon"
                aria-hidden="true"
            ></i>
            <span style="white-space: nowrap; flex-shrink: 0">{{
                props.item.label
            }}</span>
        </h2>
        <ul
            class="nav-list"
            :aria-labelledby="headingId"
        >
            <template
                v-for="child in props.item.items"
                :key="child.key"
            >
                <li
                    v-if="
                        (child.route || child.url) &&
                        (child.showIconIfCollapsed || isNavExpanded)
                    "
                    class="nav-child"
                >
                    <a
                        v-if="child.disabled"
                        role="link"
                        aria-disabled="true"
                        :aria-label="
                            isNavExpanded ? undefined : getChildLabel(child)
                        "
                        :style="{
                            paddingInlineStart: isNavExpanded
                                ? '2rem'
                                : '0.75rem',
                        }"
                        class="nav-button p-button disabled"
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
                    <RouterLink
                        v-else-if="child.route"
                        v-slot="{ href, navigate, isExactActive }"
                        :to="child.route"
                        custom
                    >
                        <a
                            v-tooltip="{
                                value: child.label,
                                pt: {
                                    text: {
                                        style: {
                                            fontFamily:
                                                'var(--p-lingo-font-family)',
                                        },
                                    },
                                },
                                disabled: isNavExpanded,
                            }"
                            :href="href"
                            :aria-label="
                                isNavExpanded ? undefined : getChildLabel(child)
                            "
                            :aria-current="isExactActive ? 'page' : undefined"
                            :style="{
                                paddingInlineStart: isNavExpanded
                                    ? '2rem'
                                    : '0.75rem',
                            }"
                            class="nav-button p-button"
                            @click="navigate"
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
                        v-else
                        v-tooltip="{
                            value: child.label,
                            pt: {
                                text: {
                                    style: {
                                        fontFamily:
                                            'var(--p-lingo-font-family)',
                                    },
                                },
                            },
                            disabled: isNavExpanded,
                        }"
                        :href="child.url"
                        :aria-label="
                            isNavExpanded ? undefined : getChildLabel(child)
                        "
                        :style="{
                            paddingInlineStart: isNavExpanded
                                ? '2rem'
                                : '0.75rem',
                        }"
                        class="nav-button p-button"
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
                </li>
            </template>
        </ul>
    </div>
</template>

<style scoped>
.nav-header {
    margin: 0;
    font-weight: inherit;
}

.nav-list {
    list-style: none;
    margin: 0;
    padding: 0;
}

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
