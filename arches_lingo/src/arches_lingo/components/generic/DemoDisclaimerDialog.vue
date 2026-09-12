<script setup lang="ts">
import { useGettext } from "vue3-gettext";

import Button from "primevue/button";
import Dialog from "primevue/dialog";

import InlineMarkupText from "@/arches_lingo/components/generic/InlineMarkupText/InlineMarkupText.vue";
import { useDemoDisclaimer } from "@/arches_lingo/composables/useDemoDisclaimer.ts";

const { $gettext } = useGettext();

const { isDemoDisclaimerVisible, acknowledgeDemoDisclaimer } =
    useDemoDisclaimer();

const disclaimerParagraphs = [
    $gettext(
        "This demo site is for evaluation purposes only. The vocabularies loaded here should NOT be treated as an authoritative source.",
    ),
    $gettext(
        "The [Getty Art and Architecture Thesaurus® (AAT)](https://lingodemo.archesproject.org/scheme/ea43bfa0-5eda-5666-884d-2885976a28d3?hierarchy=1) and [General Multilingual Environmental Thesaurus (GEMET)](https://lingodemo.archesproject.org/scheme/4dbcfd46-9c99-57b1-86e7-8559ac277b21?hierarchy=1) are locked and included only as reference examples. The [Forum on Information Standards in Heritage (FISH)](https://lingodemo.archesproject.org/scheme/bf892ca3-c994-310a-9088-16ac74113409?hierarchy=1) has generously made their thesauri available for trial editing. For more details, visit the scheme records linked above.",
    ),
    $gettext(
        "You will automatically be logged in as a demo user with read-only access. To request an account with editing functionality to the FISH thesauri, please email us at [contact@archesproject.org](mailto:contact@archesproject.org). Be aware that the demo site is refreshed weekly on Sundays at 5:00 AM GMT, reverting all edits and additions.",
    ),
    $gettext(
        "Questions or comments can be shared on the [Arches Community Forum](https://community.archesproject.org/) using the *arches-lingo* tag.",
    ),
];
</script>

<template>
    <Dialog
        :visible="isDemoDisclaimerVisible"
        :modal="true"
        :closable="false"
        :dismissable-mask="false"
        :header="$gettext('Welcome to the Arches Lingo demo site!')"
        :style="{ width: '40rem', maxWidth: '90vw' }"
    >
        <div class="disclaimer-content">
            <p
                v-for="disclaimerParagraph of disclaimerParagraphs"
                :key="disclaimerParagraph"
                class="dialog-text"
            >
                <InlineMarkupText :markup="disclaimerParagraph" />
            </p>
        </div>

        <template #footer>
            <Button
                :label="$gettext('I Understand')"
                @click="acknowledgeDemoDisclaimer"
            />
        </template>
    </Dialog>
</template>

<style scoped>
.disclaimer-content {
    max-height: 60vh;
    overflow-y: auto;
}

.dialog-text {
    margin: 0 0 0.75rem;
    font-size: var(--p-lingo-font-size-normal);
}
</style>
