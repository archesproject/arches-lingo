<script setup lang="ts">
import { computed, onMounted, ref, watch } from "vue";

import { useGettext } from "vue3-gettext";
import { useRoute } from "vue-router";
import { useToast } from "primevue/usetoast";

import Button from "primevue/button";
import Message from "primevue/message";
import Select from "primevue/select";

import ConceptMergeDialog from "@/arches_lingo/components/concept/ConceptMerge/ConceptMergeDialog.vue";
import MatchCandidateList from "@/arches_lingo/components/concept-matching/components/MatchCandidateList.vue";
import MatchRunForm from "@/arches_lingo/components/concept-matching/components/MatchRunForm.vue";
import MergeDirectionDialog from "@/arches_lingo/components/concept-matching/components/MergeDirectionDialog.vue";

import {
    createConceptMatchRun,
    fetchConceptMatchCandidates,
    fetchConceptMatchRuns,
    fetchLingoResource,
    linkConceptMatchCandidates,
    updateConceptMatchCandidates,
} from "@/arches_lingo/api.ts";
import { useConceptStore } from "@/arches_lingo/stores/useConceptStore.ts";
import {
    CANDIDATES_PER_PAGE,
    CANDIDATE_STATUS_DISMISSED,
    CANDIDATE_STATUS_PENDING,
} from "@/arches_lingo/components/concept-matching/constants.ts";
import {
    DEFAULT_ERROR_TOAST_LIFE,
    DEFAULT_TOAST_LIFE,
    ERROR,
    SECONDARY,
    SUCCESS,
    WARN,
} from "@/arches_lingo/constants.ts";

import { getItemLabel } from "@/arches_controlled_lists/utils.ts";
import { useLanguageStore } from "@/arches_lingo/stores/useLanguageStore.ts";
import { storeToRefs } from "pinia";

import type {
    ConceptMatchCandidate,
    ConceptMatchRun,
    ConceptMatchRunRequest,
    MatchedConceptSummary,
    ResourceInstanceResult,
    SearchResultItem,
} from "@/arches_lingo/types.ts";

const CONCEPT_GRAPH_SLUG = "concept";

const { $gettext } = useGettext();
const toast = useToast();
const route = useRoute();
const conceptStore = useConceptStore();
const { selectedLanguage, systemLanguage } = storeToRefs(useLanguageStore());

const runs = ref<ConceptMatchRun[]>([]);
const activeRunId = ref<number | null>(null);
const isRunning = ref(false);

const candidates = ref<ConceptMatchCandidate[]>([]);
const selectedIds = ref<Set<number>>(new Set());
const candidateStatus = ref(CANDIDATE_STATUS_PENDING);
const firstResultIndex = ref(0);
const totalResults = ref(0);
const isLoadingCandidates = ref(false);
const isLinking = ref(false);

const mergingCandidate = ref<ConceptMatchCandidate | null>(null);
const mergeSurvivor = ref<ResourceInstanceResult | null>(null);
const mergeAbsorbedId = ref<string | null>(null);
const isPreparingMerge = ref(false);
const loadError = ref<string | null>(null);

const activeRun = computed(function () {
    return runs.value.find((run) => run.id === activeRunId.value);
});

function reportError(error: unknown, summary: string) {
    toast.add({
        severity: ERROR,
        life: DEFAULT_ERROR_TOAST_LIFE,
        summary,
        detail: error instanceof Error ? error.message : undefined,
    });
}

async function loadRuns() {
    try {
        runs.value = (await fetchConceptMatchRuns()).data;
        if (activeRunId.value === null && runs.value.length) {
            activeRunId.value = runs.value[0].id;
        }
    } catch (error) {
        reportError(error, $gettext("Could not load previous runs."));
    }
}

async function loadCandidates() {
    if (activeRunId.value === null) {
        candidates.value = [];
        totalResults.value = 0;
        return;
    }

    isLoadingCandidates.value = true;
    loadError.value = null;
    try {
        const page = await fetchConceptMatchCandidates(
            activeRunId.value,
            candidateStatus.value,
            Math.floor(firstResultIndex.value / CANDIDATES_PER_PAGE) + 1,
            CANDIDATES_PER_PAGE,
        );
        candidates.value = page.data;
        totalResults.value = page.total_results;
    } catch (error) {
        loadError.value =
            error instanceof Error ? error.message : String(error);
    } finally {
        isLoadingCandidates.value = false;
    }
}

async function onRun(request: ConceptMatchRunRequest) {
    isRunning.value = true;
    try {
        const run = await createConceptMatchRun(request);
        await loadRuns();
        activeRunId.value = run.id;
        toast.add({
            severity: SUCCESS,
            life: DEFAULT_TOAST_LIFE,
            summary: $gettext("Found %{count} candidate pair(s)", {
                count: String(run.candidate_count),
            }),
        });
    } catch (error) {
        reportError(error, $gettext("Could not detect matches."));
    } finally {
        isRunning.value = false;
    }
}

async function setStatusForSelection(status: string) {
    if (activeRunId.value === null || !selectedIds.value.size) return;

    try {
        const result = await updateConceptMatchCandidates(
            activeRunId.value,
            Array.from(selectedIds.value),
            status,
        );
        toast.add({
            severity: SUCCESS,
            life: DEFAULT_TOAST_LIFE,
            summary:
                status === CANDIDATE_STATUS_DISMISSED
                    ? $gettext("Dismissed %{count} pair(s)", {
                          count: String(result.updated),
                      })
                    : $gettext("Returned %{count} pair(s) to the queue", {
                          count: String(result.updated),
                      }),
        });
        selectedIds.value = new Set();
        await Promise.all([loadRuns(), loadCandidates()]);
    } catch (error) {
        reportError(error, $gettext("Could not update the selected pairs."));
    }
}

// A pair can be skipped for a reason the reviewer can act on, so the reasons
// are named rather than reported as a bare count.
function describeSkipped(skipped: Record<string, number>) {
    const reasons: Record<string, string> = {
        missing_uri: $gettext("no URI to point at"),
        not_editable: $gettext("neither concept can be edited"),
        missing_concept: $gettext("concept no longer exists"),
    };
    return Object.entries(skipped)
        .map(([reason, count]) => `${count} (${reasons[reason] ?? reason})`)
        .join(", ");
}

async function onLinkSelection() {
    if (activeRunId.value === null || !selectedIds.value.size) return;

    isLinking.value = true;
    try {
        const result = await linkConceptMatchCandidates(
            activeRunId.value,
            Array.from(selectedIds.value),
        );

        const detail = [];
        if (result.linked_one_way) {
            detail.push(
                $gettext(
                    "%{count} recorded on one side only, because the other concept cannot be edited.",
                    { count: String(result.linked_one_way) },
                ),
            );
        }
        if (Object.keys(result.skipped).length) {
            detail.push(
                $gettext("Skipped: %{reasons}.", {
                    reasons: describeSkipped(result.skipped),
                }),
            );
        }

        toast.add({
            severity: result.linked ? SUCCESS : WARN,
            life: DEFAULT_TOAST_LIFE,
            summary: $gettext("Linked %{count} pair(s)", {
                count: String(result.linked),
            }),
            detail: detail.join(" ") || undefined,
        });

        selectedIds.value = new Set();
        await Promise.all([loadRuns(), loadCandidates()]);
    } catch (error) {
        reportError(error, $gettext("Could not link the selected pairs."));
    } finally {
        isLinking.value = false;
    }
}

// Which side of the pair is which, once the reviewer has chosen a survivor.
const mergeAbsorbedSummary = computed(function () {
    if (!mergingCandidate.value || !mergeAbsorbedId.value) return null;
    return mergingCandidate.value.concept_a.id === mergeAbsorbedId.value
        ? mergingCandidate.value.concept_a
        : mergingCandidate.value.concept_b;
});

const mergeSurvivorSummary = computed(function () {
    if (!mergingCandidate.value || !mergeAbsorbedId.value) return null;
    return mergingCandidate.value.concept_a.id === mergeAbsorbedId.value
        ? mergingCandidate.value.concept_b
        : mergingCandidate.value.concept_a;
});

// The merge dialog takes the absorbed concept in the shape its picker emits.
// Only the id and labels are read from it: the id to fetch the resource, the
// labels to name it.
const preselectedAbsorbedConcept = computed(function () {
    const absorbed = mergeAbsorbedSummary.value;
    if (!absorbed) return undefined;
    return {
        id: absorbed.id,
        labels: absorbed.labels,
        parents: [],
        polyhierarchical: false,
    } as SearchResultItem;
});

function nameOf(concept: MatchedConceptSummary) {
    return getItemLabel(
        concept,
        selectedLanguage.value.code,
        systemLanguage.value.code,
    ).value;
}

function onMergeRequested(candidateId: number) {
    mergingCandidate.value =
        candidates.value.find((candidate) => candidate.id === candidateId) ??
        null;
}

// The pair is symmetric, so the reviewer says which concept survives; only then
// is the surviving concept fetched in the shape the merge dialog expects.
async function onDirectionChosen(survivorId: string, absorbedId: string) {
    const candidate = mergingCandidate.value;
    if (!candidate) return;

    isPreparingMerge.value = true;
    try {
        mergeSurvivor.value = await fetchLingoResource(
            CONCEPT_GRAPH_SLUG,
            survivorId,
        );
        mergeAbsorbedId.value = absorbedId;
    } catch (error) {
        reportError(error, $gettext("Could not open the merge."));
        mergingCandidate.value = null;
    } finally {
        isPreparingMerge.value = false;
    }
}

function closeMerge() {
    mergingCandidate.value = null;
    mergeSurvivor.value = null;
    mergeAbsorbedId.value = null;
}

async function onMergeCompleted() {
    closeMerge();
    toast.add({
        severity: SUCCESS,
        life: DEFAULT_TOAST_LIFE,
        summary: $gettext("Concepts merged"),
    });
    // The server settles the pair, so the queue is reloaded rather than patched.
    await Promise.all([loadRuns(), loadCandidates()]);
}

function onSelectionChange(candidateId: number, isSelected: boolean) {
    const updated = new Set(selectedIds.value);
    if (isSelected) {
        updated.add(candidateId);
    } else {
        updated.delete(candidateId);
    }
    selectedIds.value = updated;
}

function onSelectAllOnPage(isSelected: boolean) {
    const updated = new Set(selectedIds.value);
    for (const candidate of candidates.value) {
        if (isSelected) {
            updated.add(candidate.id);
        } else {
            updated.delete(candidate.id);
        }
    }
    selectedIds.value = updated;
}

function onStatusChange(newStatus: string) {
    candidateStatus.value = newStatus;
    firstResultIndex.value = 0;
    selectedIds.value = new Set();
}

// A run or status change starts the review over; a page change keeps the
// selection, so a reviewer can gather pairs across pages before acting.
watch([activeRunId, candidateStatus, firstResultIndex], loadCandidates);
watch(activeRunId, () => (selectedIds.value = new Set()));

onMounted(async () => {
    try {
        await conceptStore.initialize();
    } catch (error) {
        reportError(error, $gettext("Could not load schemes."));
    }

    // Arriving from a concept's own page: look for that concept's matches
    // straight away rather than making the reviewer re-enter what they just
    // came from. A run this narrow takes well under a second.
    const conceptId = route.query.concept;
    if (typeof conceptId === "string" && conceptId) {
        await onRun({ source_concept_ids: [conceptId] });
        return;
    }

    await loadRuns();
    await loadCandidates();
});
</script>

<template>
    <div class="matches-page">
        <div class="matches-criteria">
            <h2>{{ $gettext("Find Matching Concepts") }}</h2>
            <p class="matches-intro">
                {{
                    $gettext(
                        "Look for concepts that probably mean the same thing, then dismiss the ones that do not.",
                    )
                }}
            </p>

            <MatchRunForm
                :schemes="conceptStore.schemes"
                :is-running="isRunning"
                @run="onRun"
            />
        </div>

        <div class="matches-results">
            <div class="matches-results-header">
                <Select
                    v-model="activeRunId"
                    :options="runs"
                    option-value="id"
                    :placeholder="$gettext('No runs yet')"
                    :disabled="!runs.length"
                    class="run-select"
                >
                    <template #value="{ value }">
                        <span v-if="activeRun">
                            {{
                                $gettext(
                                    "%{pending} of %{total} left to review",
                                    {
                                        pending: String(
                                            activeRun.pending_count,
                                        ),
                                        total: String(
                                            activeRun.candidate_count,
                                        ),
                                    },
                                )
                            }}
                        </span>
                        <span v-else>{{ value }}</span>
                    </template>
                    <template #option="{ option }">
                        {{
                            $gettext("%{count} pairs", {
                                count: String(option.candidate_count),
                            })
                        }}
                        — {{ new Date(option.created).toLocaleString() }}
                    </template>
                </Select>

                <div class="matches-actions">
                    <Button
                        v-if="candidateStatus === CANDIDATE_STATUS_PENDING"
                        icon="pi pi-link"
                        :label="
                            $gettext('Link %{count}', {
                                count: String(selectedIds.size),
                            })
                        "
                        :disabled="!selectedIds.size || isLinking"
                        :loading="isLinking"
                        class="action-button"
                        @click="onLinkSelection"
                    />
                    <Button
                        v-if="candidateStatus === CANDIDATE_STATUS_PENDING"
                        icon="pi pi-times"
                        :label="
                            $gettext('Dismiss %{count}', {
                                count: String(selectedIds.size),
                            })
                        "
                        :severity="SECONDARY"
                        :outlined="true"
                        :disabled="!selectedIds.size"
                        class="action-button"
                        @click="
                            setStatusForSelection(CANDIDATE_STATUS_DISMISSED)
                        "
                    />
                    <Button
                        v-else
                        icon="pi pi-undo"
                        :label="
                            $gettext('Restore %{count}', {
                                count: String(selectedIds.size),
                            })
                        "
                        :severity="SECONDARY"
                        :outlined="true"
                        :disabled="!selectedIds.size"
                        class="action-button"
                        @click="setStatusForSelection(CANDIDATE_STATUS_PENDING)"
                    />
                </div>
            </div>

            <Message
                v-if="loadError"
                :severity="ERROR"
                :closable="false"
            >
                {{ loadError }}
            </Message>

            <MatchCandidateList
                :candidates="candidates"
                :selected-ids="selectedIds"
                :is-loading="isLoadingCandidates"
                :total-results="totalResults"
                :items-per-page="CANDIDATES_PER_PAGE"
                :first-result-index="firstResultIndex"
                :status="candidateStatus"
                @update:selected="onSelectionChange"
                @select-all-on-page="onSelectAllOnPage"
                @page="firstResultIndex = $event"
                @set-status="onStatusChange"
                @merge="onMergeRequested"
            />
        </div>

        <MergeDirectionDialog
            v-if="mergingCandidate && !mergeSurvivor"
            :concept-a="mergingCandidate.concept_a"
            :concept-b="mergingCandidate.concept_b"
            :name-of="nameOf"
            :is-loading="isPreparingMerge"
            @confirm="onDirectionChosen"
            @cancel="closeMerge"
        />

        <ConceptMergeDialog
            v-if="mergeSurvivor && mergeAbsorbedId && mergingCandidate"
            :survivor-concept="mergeSurvivor"
            :survivor-label="
                mergeSurvivorSummary ? nameOf(mergeSurvivorSummary) : undefined
            "
            :scheme-id="mergeSurvivorSummary?.scheme_id ?? ''"
            :graph-slug="CONCEPT_GRAPH_SLUG"
            :preselected-concept="preselectedAbsorbedConcept"
            @merged="onMergeCompleted"
            @cancel="closeMerge"
        />
    </div>
</template>

<style scoped>
.matches-page {
    display: grid;
    grid-template-columns: 22rem 1fr;
    gap: 1.5rem;
    padding: 1.5rem;
    height: 100%;
    min-height: 0;
    overflow-y: auto;
}

.matches-criteria {
    display: flex;
    flex-direction: column;
    gap: 1rem;
}

.matches-criteria h2 {
    margin: 0;
    font-size: var(--p-lingo-font-size-medium);
    font-weight: var(--p-lingo-font-weight-normal);
    color: var(--p-neutral-500);
}

.matches-intro {
    margin: 0;
    font-size: var(--p-lingo-font-size-smallnormal);
    color: var(--p-header-item-label);
}

.matches-results {
    display: flex;
    flex-direction: column;
    gap: 0.75rem;
    min-width: 0;
}

.matches-results-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    gap: 1rem;
}

.matches-actions {
    display: flex;
    gap: 0.5rem;
}

.action-button,
.run-select {
    font-size: var(--p-lingo-font-size-small);
    border-radius: 0.125rem;
}

@media (max-width: 64rem) {
    .matches-page {
        grid-template-columns: 1fr;
    }
}
</style>
