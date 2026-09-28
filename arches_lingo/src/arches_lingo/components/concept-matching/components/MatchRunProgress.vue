<script setup lang="ts">
import { computed, onBeforeUnmount, ref, watch } from "vue";

import { useGettext } from "vue3-gettext";

import ProgressBar from "primevue/progressbar";

import { RUN_STATUS_PENDING } from "@/arches_lingo/components/concept-matching/constants.ts";
import { splitElapsedSeconds } from "@/arches_lingo/components/concept-matching/utils.ts";

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
    const { minutes, seconds } = splitElapsedSeconds(
        elapsedAtLastPoll.value + secondsSincePoll,
    );
    return minutes
        ? $gettext("%{minutes}m %{seconds}s", {
              minutes: String(minutes),
              seconds: String(seconds).padStart(2, "0"),
          })
        : $gettext("%{seconds}s", { seconds: String(seconds) });
});

const statusText = computed(function () {
    return run.status === RUN_STATUS_PENDING
        ? $gettext("Waiting for a worker to pick this up\u2026")
        : $gettext("Searching for matches\u2026");
});
</script>

<template>
    <div class="run-progress">
        <ProgressBar
            mode="indeterminate"
            :aria-label="statusText"
            class="run-progress-bar"
        />

        <div class="run-progress-detail">
            <!-- Announced as it changes; the clock beside it ticks every second
                 and would drown it out if it were announced too. -->
            <span aria-live="polite">
                {{ statusText }}
                {{
                    $gettext("%{count} found so far", {
                        count: String(run.candidate_count),
                    })
                }}
            </span>
            <span class="run-progress-numbers">
                {{ $gettext("%{elapsed} elapsed", { elapsed: elapsed }) }}
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
