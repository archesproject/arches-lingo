<script setup lang="ts">
import { onMounted, ref } from "vue";

import { useGettext } from "vue3-gettext";
import Button from "primevue/button";
import Dialog from "primevue/dialog";
import RadioButton from "primevue/radiobutton";
import Skeleton from "primevue/skeleton";

import { DANGER, SECONDARY } from "@/arches_lingo/constants.ts";
import { useConceptStore } from "@/arches_lingo/stores/useConceptStore.ts";
import type { Concept, DeleteConceptStrategy } from "@/arches_lingo/types.ts";

const props = defineProps<{
    conceptId: string;
    conceptName: string | undefined;
}>();

const emit = defineEmits<{
    confirm: [strategy: DeleteConceptStrategy | null];
    cancel: [];
}>();

const { $gettext } = useGettext();

const narrower = ref<Concept[]>([]);
const isLoading = ref(true);
const selectedStrategy = ref<DeleteConceptStrategy>("reparent");

const conceptStore = useConceptStore();

onMounted(async () => {
    try {
        await conceptStore.initialize();
        narrower.value = conceptStore.getNarrower(props.conceptId);
    } finally {
        isLoading.value = false;
    }
});

function onConfirm() {
    emit("confirm", narrower.value.length > 0 ? selectedStrategy.value : null);
}
</script>

<template>
    <Dialog
        :visible="true"
        :modal="true"
        :header="$gettext('Delete Concept')"
        class="delete-concept-dialog"
        @update:visible="$emit('cancel')"
    >
        <Skeleton
            v-if="isLoading"
            class="loading-skeleton"
        />

        <div
            v-else-if="narrower.length === 0"
            class="dialog-body"
        >
            <div class="dialog-text">
                {{ $gettext("Are you sure you want to delete") }}
                "<span class="concept-name">{{ conceptName }}</span
                >"?
            </div>
            <div class="muted-note">
                {{ $gettext("This action cannot be undone.") }}
            </div>
        </div>

        <div
            v-else
            class="dialog-body"
        >
            <div class="dialog-text">
                "<span class="concept-name">{{ conceptName }}</span
                >"
                {{
                    $gettext(
                        "has %{count} direct child concept(s). How should they be handled?",
                        { count: String(narrower.length) },
                    )
                }}
            </div>

            <div class="strategy-options">
                <label
                    class="strategy-option"
                    :class="{ selected: selectedStrategy === 'reparent' }"
                    for="strategy-reparent"
                >
                    <RadioButton
                        v-model="selectedStrategy"
                        input-id="strategy-reparent"
                        value="reparent"
                    />
                    <div class="strategy-label">
                        <span class="strategy-title">{{
                            $gettext("Attach children to parent")
                        }}</span>
                        <span class="strategy-desc">{{
                            $gettext(
                                "Child concepts will be moved up to this concept's parent. For polyhierarchical concepts, all parents will receive the children.",
                            )
                        }}</span>
                    </div>
                </label>

                <label
                    class="strategy-option"
                    :class="{
                        selected: selectedStrategy === 'delete_children',
                    }"
                    for="strategy-delete"
                >
                    <RadioButton
                        v-model="selectedStrategy"
                        input-id="strategy-delete"
                        value="delete_children"
                    />
                    <div class="strategy-label">
                        <span class="strategy-title">{{
                            $gettext("Delete all children")
                        }}</span>
                        <span class="strategy-desc">{{
                            $gettext(
                                "This concept and all its descendants will be permanently deleted.",
                            )
                        }}</span>
                    </div>
                </label>

                <label
                    class="strategy-option"
                    :class="{ selected: selectedStrategy === 'orphan' }"
                    for="strategy-orphan"
                >
                    <RadioButton
                        v-model="selectedStrategy"
                        input-id="strategy-orphan"
                        value="orphan"
                    />
                    <div class="strategy-label">
                        <span class="strategy-title">{{
                            $gettext("Leave children without parent")
                        }}</span>
                        <span class="strategy-desc warning-desc">
                            <i class="pi pi-exclamation-triangle" />
                            {{
                                $gettext(
                                    "Children will lose their hierarchical position and must be manually reassigned.",
                                )
                            }}
                        </span>
                    </div>
                </label>
            </div>
        </div>

        <template #footer>
            <Button
                :label="$gettext('Cancel')"
                :severity="SECONDARY"
                outlined
                @click="$emit('cancel')"
            />
            <Button
                :label="$gettext('Delete')"
                :severity="DANGER"
                :disabled="isLoading"
                @click="onConfirm"
            />
        </template>
    </Dialog>
</template>

<style scoped>
.delete-concept-dialog {
    width: 34rem;
}

.loading-skeleton {
    height: 4rem;
}

.dialog-body {
    display: flex;
    flex-direction: column;
    gap: 0.75rem;
}

.dialog-text {
    margin: 0;
    font-size: var(--p-lingo-font-size-normal);
}

.concept-name {
    font-weight: bold;
}

.muted-note {
    color: var(--p-text-muted-color);
    font-size: var(--p-lingo-font-size-smallnormal) !important;
}

.strategy-options {
    display: flex;
    flex-direction: column;
    gap: 0.5rem;
}

.strategy-option {
    display: flex;
    align-items: flex-start;
    gap: 0.75rem;
    padding: 0.75rem;
    border: 0.0625rem solid var(--p-content-border-color);
    border-radius: 0.25rem;
    cursor: pointer;
    transition:
        border-color 0.15s,
        background-color 0.15s;
}

.strategy-option.selected {
    border-color: var(--p-primary-color);
    background-color: var(--p-highlight-background);
}

.strategy-label {
    display: flex;
    flex-direction: column;
    gap: 0.25rem;
    min-width: 0;
}

.strategy-title {
    font-size: var(--p-lingo-font-size-normal);
    color: var(--p-text-color);
}

.strategy-desc {
    font-size: var(--p-lingo-font-size-smallnormal);
    color: var(--p-text-muted-color);
}

.warning-desc {
    color: var(--p-warn-message-color, var(--p-orange-500));
    display: flex;
    align-items: flex-start;
    gap: 0.3rem;
}

.warning-desc .pi {
    flex-shrink: 0;
    margin-top: 0.15rem;
}
</style>
