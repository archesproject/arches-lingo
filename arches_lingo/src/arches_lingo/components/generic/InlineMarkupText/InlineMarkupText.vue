<script setup lang="ts">
import { computed } from "vue";

import { parseInlineMarkup } from "@/arches_lingo/components/generic/InlineMarkupText/parseInlineMarkup.ts";

const props = defineProps<{ markup: string }>();

const segments = computed(() => parseInlineMarkup(props.markup));

function isExternalLink(url: string) {
    return !url.startsWith("mailto:");
}
</script>

<!--
    Tags are packed together deliberately: any newline between them would become
    stray whitespace in the middle of a sentence.  Each segment carries its own
    spacing from the parsed message.
-->
<template>
    <span
        ><template
            v-for="(segment, index) of segments"
            :key="index"
            ><a
                v-if="segment.url"
                :href="segment.url"
                :target="isExternalLink(segment.url) ? '_blank' : undefined"
                :rel="
                    isExternalLink(segment.url)
                        ? 'noopener noreferrer'
                        : undefined
                "
                >{{ segment.text }}</a
            ><strong v-else-if="segment.style === 'strong'">{{
                segment.text
            }}</strong
            ><em v-else-if="segment.style === 'emphasis'">{{ segment.text }}</em
            ><template v-else>{{ segment.text }}</template></template
        ></span
    >
</template>
