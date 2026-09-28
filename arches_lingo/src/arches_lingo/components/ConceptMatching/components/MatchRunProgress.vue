<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from "vue";

import { useGettext } from "vue3-gettext";

import ProgressBar from "primevue/progressbar";

import {
    ELAPSED_CLOCK_TICK_MS,
    RUN_STATUS_PENDING,
} from "@/arches_lingo/components/ConceptMatching/constants.ts";
import { splitElapsedSeconds } from "@/arches_lingo/components/ConceptMatching/utils.ts";

import type { ConceptMatchRunStatus } from "@/arches_lingo/types.ts";

const { status, candidateCount, elapsedSeconds } = defineProps<{
    status: ConceptMatchRunStatus;
    candidateCount: number;
    elapsedSeconds: number;
}>();

const { $gettext } = useGettext();

// The server says how long the run has been going; only the time since the
// last poll is measured here, where both readings come from the same clock.
const elapsedAtLastPoll = ref(elapsedSeconds);
const polledAt = ref(Date.now());
const now = ref(Date.now());

let clockTimer: ReturnType<typeof setInterval> | undefined;

const elapsedText = computed(function () {
    const secondsSincePoll = Math.max(
        0,
        Math.floor((now.value - polledAt.value) / ELAPSED_CLOCK_TICK_MS),
    );
    const { minutes, seconds } = splitElapsedSeconds(
        elapsedAtLastPoll.value + secondsSincePoll,
    );
    const clock = minutes
        ? $gettext("%{minutes}m %{seconds}s", {
              minutes: String(minutes),
              seconds: String(seconds).padStart(2, "0"),
          })
        : $gettext("%{seconds}s", { seconds: String(seconds) });
    return $gettext("%{elapsed} elapsed", { elapsed: clock });
});

const statusText = computed(() =>
    status === RUN_STATUS_PENDING
        ? $gettext("Waiting for a worker to pick this up…")
        : $gettext("Searching for matches…"),
);

const foundText = computed(() =>
    $gettext("%{count} found so far", { count: String(candidateCount) }),
);

watch(
    () => elapsedSeconds,
    function (serverElapsedSeconds) {
        elapsedAtLastPoll.value = serverElapsedSeconds;
        polledAt.value = Date.now();
        now.value = Date.now();
    },
);

onMounted(() => {
    clockTimer = setInterval(
        () => (now.value = Date.now()),
        ELAPSED_CLOCK_TICK_MS,
    );
});

onBeforeUnmount(() => clearInterval(clockTimer));
</script>

<template>
    <div class="run-progress">
        <ProgressBar
            class="run-progress-bar"
            mode="indeterminate"
            :aria-label="statusText"
        />

        <div class="run-progress-detail">
            <!-- The clock beside this ticks every second and would drown it out
                 if it were announced too. -->
            <span aria-live="polite">
                <span>{{ statusText }}</span>
                <span>{{ foundText }}</span>
            </span>
            <span class="run-progress-numbers">{{ elapsedText }}</span>
        </div>

        <p class="run-progress-note">
            {{
                $gettext(
                    "This runs on the server, so you can leave this page and come back to it. Results appear here as they are found.",
                )
            }}
        </p>
    </div>
</template>

<style scoped>
.run-progress {
    display: flex;
    flex-direction: column;
    gap: 0.5rem;
    padding: 0.75rem;
    border: 0.0625rem solid var(--p-content-border-color);
    border-radius: 0.125rem;
    background: var(--p-content-background);
}

.run-progress .run-progress-bar {
    height: 0.375rem;
}

.run-progress .run-progress-detail {
    display: flex;
    justify-content: space-between;
    gap: 1rem;
    font-size: var(--p-lingo-font-size-smallnormal);
}

.run-progress-detail > span {
    display: flex;
    gap: 0.5rem;
}

.run-progress-detail .run-progress-numbers {
    color: var(--p-text-muted-color);
    white-space: nowrap;
}

.run-progress .run-progress-note {
    margin: 0;
    font-size: var(--p-lingo-font-size-xxsmall);
    color: var(--p-text-muted-color);
}
</style>
