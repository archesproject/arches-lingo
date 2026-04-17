<script setup lang="ts">
import { computed, onMounted, ref } from "vue";

import { useGettext } from "vue3-gettext";
import Button from "primevue/button";
import Dialog from "primevue/dialog";
import RadioButton from "primevue/radiobutton";
import Skeleton from "primevue/skeleton";

import {
    DANGER,
    DELETE,
    DEPRECATE,
    SECONDARY,
    STRATEGY_DELETE_CHILDREN,
    STRATEGY_REPARENT,
} from "@/arches_lingo/constants.ts";
import { useConceptStore } from "@/arches_lingo/stores/useConceptStore.ts";
import type { Concept, DeleteConceptStrategy } from "@/arches_lingo/types.ts";

const props = defineProps<{
    conceptId: string;
    conceptName: string | undefined;
    mode: typeof DELETE | typeof DEPRECATE;
    isLoading?: boolean;
}>();

const emit = defineEmits<{
    confirm: [strategy: DeleteConceptStrategy | null];
    cancel: [];
}>();

const { $gettext } = useGettext();
const conceptStore = useConceptStore();

const narrower = ref<Concept[]>([]);
const isFetchingChildren = ref(true);
const selectedStrategy = ref<DeleteConceptStrategy>(STRATEGY_REPARENT);

onMounted(async () => {
    try {
        await conceptStore.initialize();
        narrower.value = await conceptStore.loadChildren(props.conceptId);
    } finally {
        isFetchingChildren.value = false;
    }
});

const isDelete = computed(function () {
    return props.mode === DELETE;
});

const dialogHeader = computed(function () {
    if (isDelete.value) {
        return $gettext("Delete Concept");
    } else {
        return $gettext("Deprecate Concept");
    }
});

const confirmationText = computed(function () {
    if (isDelete.value) {
        return $gettext('Are you sure you want to delete "%{name}"?', {
            name: props.conceptName ?? "",
        });
    } else {
        return $gettext('Are you sure you want to deprecate "%{name}"?', {
            name: props.conceptName ?? "",
        });
    }
});

const deleteChildrenTitle = computed(function () {
    if (isDelete.value) {
        return $gettext("Delete all children");
    } else {
        return $gettext("Deprecate all children");
    }
});

const deleteChildrenDesc = computed(function () {
    if (isDelete.value) {
        return $gettext(
            "This concept and all its descendants will be permanently deleted.",
        );
    } else {
        return $gettext(
            "This concept and all its descendants will be deprecated.",
        );
    }
});

const childrenText = computed(function () {
    return $gettext(
        '"%{name}" has %{count} direct child concept(s). How should they be handled?',
        {
            name: props.conceptName ?? "",
            count: String(narrower.value.length),
        },
    );
});

const confirmButtonLabel = computed(function () {
    if (isDelete.value) {
        return $gettext("Delete");
    } else {
        return $gettext("Deprecate");
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
        :header="dialogHeader"
        :closable="!isLoading"
        class="delete-concept-dialog"
        @update:visible="!isLoading && $emit('cancel')"
    >
        <Skeleton
            v-if="isFetchingChildren"
            class="loading-skeleton"
        />

        <div
            v-else-if="narrower.length === 0"
            class="dialog-body"
        >
            <div class="dialog-text">{{ confirmationText }}</div>
            <div class="muted-note">
                {{
                    isDelete
                        ? $gettext("This action cannot be undone.")
                        : $gettext("This concept can be reinstated later.")
                }}
            </div>
        </div>

        <div
            v-else
            class="dialog-body"
        >
            <div class="dialog-text">{{ childrenText }}</div>

            <div class="strategy-options">
                <label
                    class="strategy-option"
                    :class="{
                        selected: selectedStrategy === STRATEGY_REPARENT,
                    }"
                    for="strategy-reparent"
                >
                    <RadioButton
                        v-model="selectedStrategy"
                        input-id="strategy-reparent"
                        :value="STRATEGY_REPARENT"
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
                        selected: selectedStrategy === STRATEGY_DELETE_CHILDREN,
                    }"
                    for="strategy-delete"
                >
                    <RadioButton
                        v-model="selectedStrategy"
                        input-id="strategy-delete"
                        :value="STRATEGY_DELETE_CHILDREN"
                    />
                    <div class="strategy-label">
                        <span class="strategy-title">{{
                            deleteChildrenTitle
                        }}</span>
                        <span class="strategy-desc">{{
                            deleteChildrenDesc
                        }}</span>
                    </div>
                </label>
            </div>
        </div>

        <template #footer>
            <Button
                :label="$gettext('Cancel')"
                :severity="SECONDARY"
                :disabled="isLoading"
                :outlined="true"
                @click="$emit('cancel')"
            />
            <Button
                :label="confirmButtonLabel"
                :severity="DANGER"
                :disabled="isFetchingChildren || isLoading"
                :loading="isLoading"
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
</style>
