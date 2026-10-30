<script setup lang="ts">
import { computed, nextTick, ref, useTemplateRef } from "vue";
import { useGettext } from "vue3-gettext";

import Button from "primevue/button";

import ArchesLingoBadge from "@/arches_lingo/components/header/PageHeader/components/ArchesLingoBadge.vue";
import SideNavLinks from "@/arches_lingo/components/sidenav/components/SideNavLinks.vue";

import type { ComponentPublicInstance } from "vue";

const { $gettext } = useGettext();

const isNavExpanded = ref(false);

const navButtonLabel = computed(() =>
    $gettext("%{appName} navigation", { appName: $gettext("Lingo") }),
);

const navButton = useTemplateRef<ComponentPublicInstance>("navButton");
const buttonKey = ref(0);

async function toggleAll() {
    isNavExpanded.value = !isNavExpanded.value;
    emit("update:isNavExpanded", isNavExpanded.value);

    buttonKey.value += 1; // Force re-render of the button to remove tooltip

    // The re-render replaces the focused button, so restore focus to the
    // new one rather than letting it drop to <body>.
    await nextTick();
    (navButton.value?.$el as HTMLElement | undefined)?.focus();
}

const emit = defineEmits(["update:isNavExpanded"]);
</script>

<template>
    <div
        class="sidenav"
        :class="{ expanded: isNavExpanded }"
    >
        <Button
            ref="navButton"
            :key="buttonKey"
            v-tooltip.bottom="{
                value: $gettext('Expand navigation'),
                disabled: isNavExpanded,
                showDelay: 300,
                pt: {
                    root: { style: { marginInlineStart: '3rem' } },
                    text: {
                        style: {
                            fontFamily: 'var(--p-lingo-font-family)',
                            fontSize: 'var(--p-lingo-font-size-xsmall)',
                        },
                    },
                    arrow: { style: { display: 'none' } },
                },
            }"
            class="nav-button"
            :class="{ expanded: isNavExpanded }"
            :aria-label="navButtonLabel"
            :aria-expanded="isNavExpanded"
            @click="toggleAll"
        >
            <i
                v-if="!isNavExpanded"
                class="pi pi-bars toggle-icon"
                aria-hidden="true"
            />

            <ArchesLingoBadge
                v-if="isNavExpanded"
                :is-link="false"
            />
        </Button>
        <SideNavLinks :is-expanded="isNavExpanded" />
    </div>
</template>

<style scoped>
.sidenav {
    width: 3rem;
    background: var(--p-primary-950);
    border-right: 0.125rem solid var(--p-primary-950);
    transition: width 0.3s ease-in-out;
}

.sidenav.expanded {
    width: 16rem;
}

.p-button {
    height: 2.5rem;
    font-size: var(--p-lingo-font-size-large);
    background: var(--p-primary-950) !important;
    border-radius: 0;
    border: none;
}

.nav-button {
    border: 0 !important;
    border-bottom: 0.125rem solid var(--p-primary-950) !important;
    cursor: pointer;
    height: 3.125rem !important;
}

.nav-button.expanded {
    background: var(--p-lingo-navigation-bar-background) !important;
    padding-inline-start: 0.6rem;
}

.nav-button:hover {
    background: var(--p-lingo-navigation-bar-hover-background) !important;
}

:deep(.p-button) {
    background-color: var(--p-primary-950) !important;
    border-color: var(--p-primary-950) !important;
    color: var(--p-lingo-navigation-bar-color) !important;
}
:deep(.p-button):hover {
    background: var(--p-lingo-navigation-bar-hover-background) !important;
}

:deep(.nav-button) {
    height: 2.75rem;
    width: 100%;
    border-radius: 0;
    text-decoration: none;
    justify-content: flex-start;
    font-size: var(--p-lingo-font-size-xsmall);

    i {
        font-size: var(--p-lingo-font-size-xsmall);
        padding: 0rem 0rem 0rem 0.25rem;
    }
}

@media screen and (max-width: 960px) {
    .sidenav {
        display: none;
    }
}
</style>
