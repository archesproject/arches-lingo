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
        "**This demo site is for evaluation purposes only.** The vocabularies loaded here should **NOT** be treated as an authoritative source.",
    ),
    $gettext(
        "The *Getty Art and Architecture Thesaurus® (AAT)* and *General Multilingual Environmental Thesaurus (GEMET)* are locked (as of the dates they were loaded) and are not editable. They are included here only to demonstrate navigating, searching, and matching across vocabularies. The *Forum on Information Standards in Heritage (FISH)* has generously made their thesauri available for trial editing in a demo environment primarily to allow visitors to explore the flexibility and functionality of Lingo, including how vocabularies can be managed, modified, and extended.",
    ),
    $gettext(
        "Should you make trial edits to the *FISH* vocabularies be aware that the **site is refreshed weekly on Sunday**, reverting all edits and additions.",
    ),
    $gettext(
        "To access editing functionality to *FISH*, please request an account by emailing us at [contact@archesproject.org](mailto:contact@archesproject.org?subject=Lingo%20Demo%20Editing%20Access) with the subject \u201cLingo Demo Editing Access.\u201d Questions or comments can be shared on the [Arches Community Forum](https://community.archesproject.org/) using the arches-lingo tag.",
    ),
    $gettext("For official vocabularies, see:"),
];

const officialVocabularyLinks = [
    {
        label: $gettext("FISH Thesauri"),
        url: "https://heritage-standards.org.uk/fish-vocabularies/",
    },
    {
        label: $gettext("Getty AAT®"),
        url: "https://www.getty.edu/research/tools/vocabularies/aat/",
    },
    {
        label: $gettext("GEMET"),
        url: "https://www.eionet.europa.eu/gemet/en/about/",
    },
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

            <ul class="official-vocabulary-list">
                <li
                    v-for="officialVocabularyLink of officialVocabularyLinks"
                    :key="officialVocabularyLink.url"
                >
                    <a
                        :href="officialVocabularyLink.url"
                        target="_blank"
                        rel="noopener noreferrer"
                    >
                        {{ officialVocabularyLink.label }}
                    </a>
                </li>
            </ul>
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

.official-vocabulary-list {
    margin: 0;
    padding-inline-start: 1.5rem;
    font-size: var(--p-lingo-font-size-normal);
}

.official-vocabulary-list li {
    margin-bottom: 0.25rem;
}
</style>
