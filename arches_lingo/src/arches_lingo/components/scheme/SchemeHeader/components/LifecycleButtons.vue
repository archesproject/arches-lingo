<script setup lang="ts">
import { computed, onMounted, ref, watch } from "vue";
import { useGettext } from "vue3-gettext";
import { useToast } from "primevue/usetoast";

import Button from "primevue/button";
import Skeleton from "primevue/skeleton";

import {
    fetchResourceInstanceLifecycleState,
    updateResourceInstanceLifecycleState,
} from "@/arches_lingo/api.ts";

import {
    DANGER,
    DEFAULT_ERROR_TOAST_LIFE,
    EDITING_LIFECYCLE_STATE_ID,
    ERROR,
    RETIRED_LIFECYCLE_STATE_ID,
} from "@/arches_lingo/constants.ts";

type ResourceInstanceLifecycleState = {
    id: string;
    name: string;
    action_label: string;
    next_resource_instance_lifecycle_states?: ResourceInstanceLifecycleState[];
};

const props = defineProps<{
    resourceInstanceId: string | undefined;
    buttonClass?: string;
    retireReinstateOnly?: boolean;
}>();

const emit = defineEmits<{
    (
        eventName: "change",
        currentResourceInstanceLifecycleState: ResourceInstanceLifecycleState,
    ): void;
    (eventName: "retire-requested", nextStateId: string): void;
    (eventName: "reinstate-requested", nextStateId: string): void;
}>();

defineExpose({ executeTransition, refreshLifecycleState });

const toast = useToast();
const { $gettext } = useGettext();

const isLoading = ref(false);
const activeRequestStateId = ref<string | undefined>();
const currentResourceInstanceLifecycleState = ref<
    ResourceInstanceLifecycleState | undefined
>();

const isCurrentlyRetired = computed(() => {
    return (
        currentResourceInstanceLifecycleState.value?.id ===
        RETIRED_LIFECYCLE_STATE_ID
    );
});

const nextResourceInstanceLifecycleStates = computed(() => {
    const states =
        currentResourceInstanceLifecycleState.value
            ?.next_resource_instance_lifecycle_states || [];
    if (!props.retireReinstateOnly) return states;
    if (isCurrentlyRetired.value) return states;
    if (
        currentResourceInstanceLifecycleState.value?.id ===
        EDITING_LIFECYCLE_STATE_ID
    ) {
        return states.filter(
            (state) => state.id === RETIRED_LIFECYCLE_STATE_ID,
        );
    }
    return [];
});

async function refreshLifecycleState() {
    if (!props.resourceInstanceId) {
        currentResourceInstanceLifecycleState.value = undefined;
        return;
    }

    isLoading.value = true;
    try {
        const fetchedState = await fetchResourceInstanceLifecycleState(
            props.resourceInstanceId,
        );
        currentResourceInstanceLifecycleState.value = fetchedState;
    } catch (error) {
        toast.add({
            severity: ERROR,
            life: DEFAULT_ERROR_TOAST_LIFE,
            summary: $gettext("Unable to fetch lifecycle state"),
            detail: error instanceof Error ? error.message : undefined,
        });
    } finally {
        isLoading.value = false;
    }
}

async function executeTransition(nextStateId: string) {
    if (!props.resourceInstanceId) {
        return;
    }

    activeRequestStateId.value = nextStateId;
    try {
        const transitionResult = await updateResourceInstanceLifecycleState(
            props.resourceInstanceId,
            nextStateId,
        );

        const updatedState =
            transitionResult.current_resource_instance_lifecycle_state as ResourceInstanceLifecycleState;

        currentResourceInstanceLifecycleState.value = updatedState;
        emit("change", updatedState);
    } catch (error) {
        toast.add({
            severity: ERROR,
            life: DEFAULT_ERROR_TOAST_LIFE,
            summary: $gettext("Unable to change lifecycle state"),
            detail: error instanceof Error ? error.message : undefined,
        });
    } finally {
        activeRequestStateId.value = undefined;
    }
}

function handleButtonClick(nextState: ResourceInstanceLifecycleState) {
    if (nextState.id === RETIRED_LIFECYCLE_STATE_ID) {
        emit("retire-requested", nextState.id);
        return;
    }

    if (isCurrentlyRetired.value) {
        emit("reinstate-requested", nextState.id);
        return;
    }

    executeTransition(nextState.id);
}

function buttonSeverity(nextStateId: string): string | undefined {
    if (nextStateId === RETIRED_LIFECYCLE_STATE_ID) {
        return DANGER;
    }
    return undefined;
}

function buttonIcon(nextStateId: string): string {
    if (nextStateId === RETIRED_LIFECYCLE_STATE_ID) {
        return "pi pi-ban";
    }
    if (
        isCurrentlyRetired.value &&
        nextStateId === EDITING_LIFECYCLE_STATE_ID
    ) {
        return "pi pi-refresh";
    }
    return "pi pi-book";
}

onMounted(async () => {
    await refreshLifecycleState();
});

watch(
    () => props.resourceInstanceId,
    async () => {
        await refreshLifecycleState();
    },
);
</script>

<template>
    <div
        v-if="resourceInstanceId"
        class="lifecycle-buttons"
    >
        <Skeleton
            v-if="isLoading"
            style="width: 10rem; height: 2.25rem"
        />

        <template v-else>
            <Button
                v-for="nextState in nextResourceInstanceLifecycleStates"
                :key="nextState.id"
                :label="nextState.action_label"
                :aria-label="nextState.action_label"
                :class="buttonClass"
                :severity="buttonSeverity(nextState.id)"
                :loading="activeRequestStateId === nextState.id"
                :disabled="activeRequestStateId !== undefined"
                :icon="buttonIcon(nextState.id)"
                @click="handleButtonClick(nextState)"
            />
        </template>
    </div>
</template>

<style scoped>
.lifecycle-buttons {
    display: inline-flex;
    gap: 0.25rem;
    flex-wrap: wrap;
    justify-content: flex-end;
    min-width: 0;
}
</style>
