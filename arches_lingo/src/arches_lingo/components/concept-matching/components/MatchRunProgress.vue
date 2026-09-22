<script setup lang="ts">
import { computed, onBeforeUnmount, ref, watch } from "vue";

import { useGettext } from "vue3-gettext";

import ProgressBar from "primevue/progressbar";

import { RUN_STATUS_PENDING } from "@/arches_lingo/components/concept-matching/constants.ts";
import { formatElapsed } from "@/arches_lingo/components/concept-matching/utils.ts";

import type { ConceptMatchRun } from "@/arches_lingo/types.ts";

const { run } = defineProps<{ run: ConceptMatchRun }>();

const { $gettext } = useGettext();

// How long the search has been going. There is no total to count towards --
// the work is one index probe per label and the server does not know how many
// will match -- so elapsed time and pairs found so far are the honest signals.
//
// The server reports how long its run has been going rather than the client
// subtracting the run's timestamp from its own clock. The two clocks need not
// agree: a run timestamp carries no offset, so a browser in another zone reads
// it as its own local time and can place the start of the run in the future.
// Only the interval since the last poll is measured here, where both readings
// come from the same clock.
const elapsedAtLastPoll = ref(run.elapsed_seconds);
const polledAt = ref(Date.now());
const now = ref(Date.now());

watch(
    () => run.elapsed_seconds,
    function (serverElapsedSeconds) {
        elapsedAtLastPoll.value = serverElapsedSeconds;
        polledAt.value = Date.now();
        now.value = Date.now();
    },
);

const tick = setInterval(() => (now.value = Date.now()), 1000);
onBeforeUnmount(() => clearInterval(tick));

const elapsed = computed(function () {
    const secondsSincePoll = Math.max(
        0,
        Math.floor((now.value - polledAt.value) / 1000),
    );
    return formatElapsed(elapsedAtLastPoll.value + secondsSincePoll, $gettext);
});

const statusText = computed(function () {
    return run.status === RUN_STATUS_PENDING
        ? $gettext("Waiting for a worker to pick this up\u2026")
        : $gettext("Comparing labels\u2026");
});
</script>

<template>
    <div class="run-progress">
        <ProgressBar
            :mode="'indeterminate'"
            class="run-progress-bar"
        />

        <div class="run-progress-detail">
            <span>{{ statusText }}</span>
            <span class="run-progress-numbers">
                {{
                    $gettext(
                        "%{count} found so far \u00b7 %{elapsed} elapsed",
                        {
                            count: String(run.candidate_count),
                            elapsed: elapsed,
                        },
                    )
                }}
            </span>
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

.run-progress-bar {
    height: 0.375rem;
}

.run-progress-detail {
    display: flex;
    justify-content: space-between;
    gap: 1rem;
    font-size: var(--p-lingo-font-size-smallnormal);
}

.run-progress-numbers {
    color: var(--p-inputtext-placeholder-color);
    white-space: nowrap;
}

.run-progress-note {
    margin: 0;
    font-size: var(--p-lingo-font-size-xxsmall);
    color: var(--p-inputtext-placeholder-color);
}
</style>
