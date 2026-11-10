<script setup lang="ts">
import { computed, ref, useTemplateRef } from "vue";
import { storeToRefs } from "pinia";

import { useGettext } from "vue3-gettext";
import { useToast } from "primevue/usetoast";

import Button from "primevue/button";
import Popover from "primevue/popover";

import { fetchDereferencedResource } from "@/arches_lingo/api.ts";
import {
    DEFAULT_ERROR_TOAST_LIFE,
    ERROR,
    GET_AS_ICON,
    RDF_EXPORT_FORMATS,
} from "@/arches_lingo/constants.ts";
import { useUserStore } from "@/arches_lingo/stores/useUserStore.ts";
import {
    canUserDereferenceResource,
    triggerBlobDownload,
} from "@/arches_lingo/utils.ts";
import { sanitizeFilename } from "@/arches_controlled_lists/utils.ts";

import type { PopoverMethods } from "primevue/popover";
import type { RdfExportFormat } from "@/arches_lingo/types.ts";

const props = defineProps<{
    resourceType: "concept" | "scheme";
    resourceInstanceId: string;
    fileBaseName: string;
    lifecycleStateId?: string;
}>();

const { $gettext } = useGettext();
const toast = useToast();
const { isAnonymous } = storeToRefs(useUserStore());

const popover = useTemplateRef<PopoverMethods>("popover");
const downloadingFormatToken = ref<string | null>(null);

const isDownloadAvailable = computed(function () {
    return canUserDereferenceResource(
        isAnonymous.value,
        props.lifecycleStateId,
    );
});

function toggleMenu(event: MouseEvent) {
    popover.value!.toggle(event);
}

async function downloadAs(format: RdfExportFormat) {
    downloadingFormatToken.value = format.token;
    try {
        const blob = await fetchDereferencedResource(
            props.resourceType,
            props.resourceInstanceId,
            format.token,
        );

        if (!blob) {
            showDownloadError(
                $gettext("This resource is not available to download."),
            );
            return;
        }

        const filename = `${sanitizeFilename(props.fileBaseName)}.${format.extension}`;
        triggerBlobDownload(blob, filename);
        popover.value!.hide();
    } catch {
        showDownloadError(
            $gettext(
                "The download could not be prepared. Please try again later.",
            ),
        );
    } finally {
        downloadingFormatToken.value = null;
    }
}

function showDownloadError(detail: string) {
    toast.add({
        severity: ERROR,
        life: DEFAULT_ERROR_TOAST_LIFE,
        summary: $gettext("Unable to download resource"),
        detail,
    });
}
</script>

<template>
    <div
        v-if="isDownloadAvailable"
        class="get-as-menu"
    >
        <Button
            :icon="GET_AS_ICON"
            class="get-as-button"
            variant="link"
            :aria-label="$gettext('Get as...')"
            @click="toggleMenu"
        ></Button>
        <Popover
            ref="popover"
            class="get-as-popover"
        >
            <div class="get-as-options">
                <Button
                    v-for="format in RDF_EXPORT_FORMATS"
                    :key="format.token"
                    :label="format.label"
                    variant="text"
                    class="get-as-option"
                    :loading="downloadingFormatToken === format.token"
                    :disabled="
                        downloadingFormatToken !== null &&
                        downloadingFormatToken !== format.token
                    "
                    @click="downloadAs(format)"
                />
            </div>
        </Popover>
    </div>
</template>

<style scoped>
.get-as-menu {
    display: inline-flex;
    align-items: center;
}

.get-as-button {
    flex-shrink: 0;
    font-size: var(--p-lingo-font-size-small);
    color: var(--p-lingo-accent-color);
}

.get-as-popover {
    padding: 0.5rem;
}

.get-as-options {
    display: flex;
    flex-direction: column;
    gap: 0.25rem;
}

.get-as-option {
    justify-content: flex-start;
}
</style>
