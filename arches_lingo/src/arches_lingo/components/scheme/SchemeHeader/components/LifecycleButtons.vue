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

import { DEFAULT_ERROR_TOAST_LIFE, ERROR } from "@/arches_lingo/constants.ts";

type ResourceInstanceLifecycleState = {
    id: string;
    name: string;
    action_label: string;
    next_resource_instance_lifecycle_states?: ResourceInstanceLifecycleState[];
};

const props = defineProps<{
    resourceInstanceId: string | undefined;
    buttonClass?: string;
}>();

const emit = defineEmits<{
    (
        eventName: "change",
        currentResourceInstanceLifecycleState: ResourceInstanceLifecycleState,
    ): void;
}>();

const toast = useToast();
const { $gettext } = useGettext();

const isLoading = ref(false);
const activeRequestStateId = ref<string | undefined>();
const currentResourceInstanceLifecycleState = ref<
    ResourceInstanceLifecycleState | undefined
>();

const nextResourceInstanceLifecycleStates = computed(() => {
    return (
        currentResourceInstanceLifecycleState.value
            ?.next_resource_instance_lifecycle_states || []
    );
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

async function onUpdateLifecycleState(nextStateId: string) {
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
                :loading="activeRequestStateId === nextState.id"
                :disabled="activeRequestStateId !== undefined"
                icon="pi pi-book"
                @click="onUpdateLifecycleState(nextState.id)"
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
