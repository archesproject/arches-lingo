<script setup lang="ts">
import { useGettext } from "vue3-gettext";

import Button from "primevue/button";
import Dialog from "primevue/dialog";

import { useDemoDisclaimer } from "@/arches_lingo/composables/useDemoDisclaimer.ts";

const { $gettext } = useGettext();

const { isDemoDisclaimerVisible, acknowledgeDemoDisclaimer } =
    useDemoDisclaimer();

// TODO: replace with the actual weekly refresh day before this is shared publicly.
const siteRefreshDayOfWeek = "[DAY OF WEEK]";

const editingAccessRequestMailto =
    "mailto:contact@archesproject.org?subject=Lingo%20Demo%20Editing%20Access";
const communityForumUrl = "https://community.archesproject.org/";

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
            <p class="dialog-text">
                {{
                    $gettext(
                        "This demo site is for evaluation purposes only. The vocabularies loaded here should NOT be treated as an authoritative source.",
                    )
                }}
            </p>

            <p class="dialog-text">
                {{
                    $gettext(
                        "The Getty Art and Architecture Thesaurus® (AAT) and General Multilingual Environmental Thesaurus (GEMET) are locked (as of the dates they were loaded) and are not editable. They are included here only to demonstrate navigating, searching, and matching across vocabularies. The Forum on Information Standards in Heritage (FISH) has generously made their thesauri available for trial editing in a demo environment primarily to allow visitors to explore the flexibility and functionality of Lingo, including how vocabularies can be managed, modified, and extended.",
                    )
                }}
            </p>

            <p class="dialog-text">
                {{
                    $gettext(
                        "Should you make trial edits to the FISH vocabularies be aware that the site is refreshed every week on %{dayOfWeek}, reverting all edits and additions.",
                        { dayOfWeek: siteRefreshDayOfWeek },
                    )
                }}
            </p>

            <p class="dialog-text">
                {{
                    $gettext(
                        "To access editing functionality to FISH, please request an account by emailing us at",
                    )
                }}
                <a :href="editingAccessRequestMailto"
                    >contact@archesproject.org</a
                >
                {{ $gettext("with the subject “Lingo Demo Editing Access.”") }}
                {{ $gettext("Questions or comments can be shared on the") }}
                <a
                    :href="communityForumUrl"
                    target="_blank"
                    rel="noopener noreferrer"
                >
                    {{ $gettext("Arches Community Forum") }}
                </a>
                {{ $gettext("using the arches-lingo tag.") }}
            </p>

            <p class="dialog-text">
                {{ $gettext("For official vocabularies, see:") }}
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
