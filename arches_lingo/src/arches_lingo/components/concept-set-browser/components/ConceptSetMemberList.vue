<script setup lang="ts">
import { computed, ref } from "vue";
import { storeToRefs } from "pinia";
import { useGettext } from "vue3-gettext";
import { useRoute, useRouter } from "vue-router";

import Button from "primevue/button";
import Checkbox from "primevue/checkbox";

import LifecycleStateBadge from "@/arches_lingo/components/generic/LifecycleStateBadge.vue";
import { getItemLabel } from "@/arches_controlled_lists/utils.ts";
import { getConceptIcon } from "@/arches_lingo/utils.ts";
import { useLanguageStore } from "@/arches_lingo/stores/useLanguageStore.ts";
import { routeNames } from "@/arches_lingo/routes.ts";

import type { ConceptSetDetail } from "@/arches_lingo/types.ts";

const props = defineProps<{
    setDetail: ConceptSetDetail;
}>();

const emit = defineEmits<{
    (event: "back"): void;
    (event: "remove-members", conceptIds: string[]): void;
    (event: "add-current-concept", conceptId: string): void;
}>();

const { $gettext } = useGettext();
const route = useRoute();
const router = useRouter();
const { selectedLanguage, systemLanguage } = storeToRefs(useLanguageStore());

const isOnConceptPage = computed(() => route.name === routeNames.concept);

const currentConceptId = computed(() =>
    isOnConceptPage.value ? (route.params.id as string) : null,
);

const currentConceptIsAlreadyMember = computed(
    () =>
        currentConceptId.value !== null &&
        props.setDetail.members.some(
            (member) => member.id === currentConceptId.value,
        ),
);

const selectedConceptIds = ref<Set<string>>(new Set());

function toggleSelectConcept(conceptId: string) {
    const updatedSet = new Set(selectedConceptIds.value);
    if (updatedSet.has(conceptId)) {
        updatedSet.delete(conceptId);
    } else {
        updatedSet.add(conceptId);
    }
    selectedConceptIds.value = updatedSet;
}

function navigateToConcept(conceptId: string) {
    router.push({ name: routeNames.concept, params: { id: conceptId } });
}

function handleRemoveSelected() {
    emit("remove-members", Array.from(selectedConceptIds.value));
    selectedConceptIds.value = new Set();
}
</script>

<template>
    <div class="concept-set-member-list">
        <div class="member-list-header">
            <Button
                icon="pi pi-arrow-left"
                text
                rounded
                size="small"
                :aria-label="$gettext('Back to sets')"
                @click="emit('back')"
            />
            <div class="set-title">
                <i
                    class="pi pi-folder"
                    aria-hidden="true"
                />
                <span>{{ props.setDetail.name }}</span>
            </div>
        </div>

        <div
            v-if="props.setDetail.description"
            class="set-description"
        >
            {{ props.setDetail.description }}
        </div>

        <div class="member-actions">
            <Button
                v-if="isOnConceptPage"
                :label="
                    currentConceptIsAlreadyMember
                        ? $gettext('Already in set')
                        : $gettext('Add current concept')
                "
                icon="pi pi-plus-circle"
                size="small"
                :disabled="currentConceptIsAlreadyMember"
                @click="emit('add-current-concept', currentConceptId!)"
            />
            <Button
                :label="$gettext('Remove from Set')"
                icon="pi pi-minus-circle"
                size="small"
                severity="danger"
                outlined
                :disabled="selectedConceptIds.size === 0"
                @click="handleRemoveSelected"
            />
        </div>

        <div
            v-if="props.setDetail.members.length === 0"
            class="empty-message"
        >
            {{ $gettext("This concept set has no members.") }}
        </div>

        <ul
            v-else
            class="members-list"
        >
            <li
                v-for="member in props.setDetail.members"
                :key="member.id"
                class="member-item"
                :class="{
                    'member-item--active': member.id === currentConceptId,
                }"
            >
                <Checkbox
                    :model-value="selectedConceptIds.has(member.id)"
                    binary
                    @update:model-value="toggleSelectConcept(member.id)"
                />
                <Button
                    text
                    plain
                    :class="[
                        'member-label',
                        {
                            'member-label--active':
                                member.id === currentConceptId,
                        },
                    ]"
                    :pt="{
                        root: {
                            style: {
                                justifyContent: 'flex-start',
                                padding: '0.25rem 0',
                            },
                        },
                    }"
                    @click="navigateToConcept(member.id)"
                >
                    <i
                        :class="[getConceptIcon(member), 'concept-icon']"
                        aria-hidden="true"
                    />
                    <span>{{
                        getItemLabel(
                            member,
                            selectedLanguage.code,
                            systemLanguage.code,
                        ).value
                    }}</span>
                    <LifecycleStateBadge
                        :lifecycle-state-id="
                            member.resource_instance_lifecycle_state_id
                        "
                        :lifecycle-state-name="
                            member.resource_instance_lifecycle_state_name
                        "
                    />
                </Button>
            </li>
        </ul>
    </div>
</template>

<style scoped>
.concept-set-member-list {
    display: flex;
    flex-direction: column;
    height: 100%;
    overflow: hidden;
    font-family: var(--p-lingo-font-family);
}

.member-list-header {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    padding: 0.25rem 0.5rem;
    background: var(--p-header-toolbar-background);
    border-bottom: 0.0625rem solid var(--p-menubar-border-color);
    flex-shrink: 0;
}

.set-title {
    display: flex;
    align-items: center;
    gap: 0.375rem;
    font-size: var(--p-lingo-font-size-smallnormal);
    font-weight: var(--p-lingo-font-weight-normal);
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
}

.set-description {
    padding: 0.5rem;
    font-size: var(--p-lingo-font-size-small);
    color: var(--p-text-muted-color);
    border-bottom: 0.0625rem solid var(--p-highlight-focus-background);
    flex-shrink: 0;
}

.member-actions {
    display: flex;
    flex-wrap: wrap;
    justify-content: flex-end;
    gap: 0.375rem;
    padding: 0.5rem;
    border-bottom: 0.0625rem solid var(--p-highlight-focus-background);
    flex-shrink: 0;
}

.member-actions :deep(.p-button) {
    font-size: var(--p-lingo-font-size-xsmall);
    font-weight: var(--p-lingo-font-weight-normal);
    border-radius: 0.125rem;
}

.empty-message {
    text-align: center;
    padding: 1rem;
    color: var(--p-text-muted-color);
    font-size: var(--p-lingo-font-size-small);
    flex-shrink: 0;
}

.members-list {
    flex: 1 1 auto;
    overflow-y: auto;
    list-style: none;
    margin: 0;
    padding: 0;
}

.member-item {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    padding: 0.375rem 0.5rem;
    border-radius: 0.125rem;
}

.member-item:hover {
    background-color: var(--p-highlight-background);
}

.member-item--active,
.member-item--active:hover {
    background: var(--p-header-button-background);
    color: var(--p-header-button-color);
}

.member-label--active.p-button,
.member-label--active.p-button:hover {
    color: var(--p-header-button-color);
}

.member-label {
    flex: 1;
    min-width: 0;
    font-family: var(--p-lingo-font-family);
    font-size: var(--p-lingo-font-size-smallnormal);
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
}

.concept-icon {
    flex-shrink: 0;
    font-size: var(--p-lingo-font-size-small);
}
</style>
