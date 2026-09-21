<script setup lang="ts">
import { computed, onMounted, ref } from "vue";

import { useGettext } from "vue3-gettext";
import Message from "primevue/message";
import RadioButton from "primevue/radiobutton";
import Skeleton from "primevue/skeleton";

import {
    ERROR,
    STRATEGY_DELETE_CHILDREN,
    STRATEGY_REPARENT,
    STRATEGY_REPARENT_TO_SURVIVOR,
} from "@/arches_lingo/constants.ts";
import { useConceptStore } from "@/arches_lingo/stores/useConceptStore.ts";

import type { Concept, MergeRetirementStrategy } from "@/arches_lingo/types.ts";

const { absorbedConceptId, absorbedLabel, survivorLabel, retirementStrategy } =
    defineProps<{
        absorbedConceptId: string;
        absorbedLabel: string | undefined;
        survivorLabel: string | undefined;
        retirementStrategy: MergeRetirementStrategy;
    }>();

const emit = defineEmits<{
    (
        event: "update:retirementStrategy",
        strategy: MergeRetirementStrategy,
    ): void;
}>();

const { $gettext } = useGettext();
const conceptStore = useConceptStore();

const children = ref<Concept[]>([]);
const isFetchingChildren = ref(true);
const fetchError = ref<string | null>(null);

const hasChildren = computed(function () {
    return children.value.length > 0;
});

const childrenText = computed(function () {
    return $gettext(
        '"%{name}" has %{count} direct child concept(s). How should they be handled when it is retired?',
        { name: absorbedLabel ?? "", count: String(children.value.length) },
    );
});

const reparentToSurvivorDesc = computed(function () {
    return $gettext('Child concepts become children of "%{survivor}".', {
        survivor: survivorLabel ?? "",
    });
});

// Without the children there is no way to know whether a choice is even called
// for, so the failure is shown rather than presenting an empty section. The merge
// stays available: the server re-checks for children and applies the default the
// dialog is already carrying.
const fetchErrorText = computed(function () {
    return $gettext(
        'Could not check whether "%{name}" has child concepts. Any children it has will be attached to the surviving concept.',
        { name: absorbedLabel ?? "" },
    );
});

onMounted(async () => {
    try {
        await conceptStore.initialize();
        children.value = await conceptStore.loadChildren(absorbedConceptId);
    } catch (error) {
        fetchError.value =
            error instanceof Error ? error.message : String(error);
    } finally {
        isFetchingChildren.value = false;
    }
});

defineExpose({ hasChildren });
</script>

<template>
    <Skeleton
        v-if="isFetchingChildren"
        class="loading-skeleton"
    />

    <Message
        v-else-if="fetchError"
        :severity="ERROR"
        :closable="false"
    >
        {{ fetchErrorText }}
    </Message>

    <div
        v-else-if="hasChildren"
        class="retirement-options"
    >
        <p class="retirement-text">{{ childrenText }}</p>

        <label
            class="retirement-option"
            :class="{
                selected: retirementStrategy === STRATEGY_REPARENT_TO_SURVIVOR,
            }"
            for="merge-strategy-survivor"
        >
            <RadioButton
                :model-value="retirementStrategy"
                input-id="merge-strategy-survivor"
                name="merge-retirement-strategy"
                :value="STRATEGY_REPARENT_TO_SURVIVOR"
                @update:model-value="
                    emit(
                        'update:retirementStrategy',
                        STRATEGY_REPARENT_TO_SURVIVOR,
                    )
                "
            />
            <span class="retirement-label">
                <span class="retirement-title">
                    {{ $gettext("Attach children to the surviving concept") }}
                </span>
                <span class="retirement-desc">{{
                    reparentToSurvivorDesc
                }}</span>
            </span>
        </label>

        <label
            class="retirement-option"
            :class="{ selected: retirementStrategy === STRATEGY_REPARENT }"
            for="merge-strategy-reparent"
        >
            <RadioButton
                :model-value="retirementStrategy"
                input-id="merge-strategy-reparent"
                name="merge-retirement-strategy"
                :value="STRATEGY_REPARENT"
                @update:model-value="
                    emit('update:retirementStrategy', STRATEGY_REPARENT)
                "
            />
            <span class="retirement-label">
                <span class="retirement-title">
                    {{ $gettext("Attach children to their existing parents") }}
                </span>
                <span class="retirement-desc">
                    {{
                        $gettext(
                            "Child concepts move up to the parents of the concept being retired. For polyhierarchical concepts, all parents receive the children.",
                        )
                    }}
                </span>
            </span>
        </label>

        <label
            class="retirement-option"
            :class="{
                selected: retirementStrategy === STRATEGY_DELETE_CHILDREN,
            }"
            for="merge-strategy-retire-children"
        >
            <RadioButton
                :model-value="retirementStrategy"
                input-id="merge-strategy-retire-children"
                name="merge-retirement-strategy"
                :value="STRATEGY_DELETE_CHILDREN"
                @update:model-value="
                    emit('update:retirementStrategy', STRATEGY_DELETE_CHILDREN)
                "
            />
            <span class="retirement-label">
                <span class="retirement-title">
                    {{ $gettext("Retire all children") }}
                </span>
                <span class="retirement-desc">
                    {{
                        $gettext(
                            "This concept and all its descendants will be retired.",
                        )
                    }}
                </span>
            </span>
        </label>
    </div>
</template>

<style scoped>
.loading-skeleton {
    height: 4rem;
}

.retirement-options {
    display: flex;
    flex-direction: column;
    gap: 0.5rem;
    padding-inline-start: 2rem;
}

.retirement-text {
    margin: 0;
    font-size: var(--p-lingo-font-size-smallnormal);
}

.retirement-option {
    display: flex;
    align-items: flex-start;
    gap: 0.75rem;
    padding: 0.625rem;
    border: 0.0625rem solid var(--p-content-border-color);
    border-radius: 0.125rem;
    cursor: pointer;
}

.retirement-option.selected {
    border-color: var(--p-primary-color);
    background-color: var(--p-highlight-background);
}

.retirement-label {
    display: flex;
    flex-direction: column;
    gap: 0.125rem;
    min-width: 0;
}

.retirement-title {
    font-size: var(--p-lingo-font-size-normal);
    color: var(--p-text-color);
}

.retirement-desc {
    font-size: var(--p-lingo-font-size-smallnormal);
    color: var(--p-text-muted-color);
}
</style>
