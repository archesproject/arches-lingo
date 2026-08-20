<script setup lang="ts">
import { ref } from "vue";
import { useGettext } from "vue3-gettext";

import Button from "primevue/button";
import Dialog from "primevue/dialog";

import { DEMO_DISCLAIMER_ACKNOWLEDGED_LOCAL_STORAGE_KEY } from "@/arches_lingo/constants.ts";

const { $gettext } = useGettext();

const isDemoDisclaimerVisible = ref(
    localStorage.getItem(DEMO_DISCLAIMER_ACKNOWLEDGED_LOCAL_STORAGE_KEY) !==
        "true",
);

function acknowledgeDemoDisclaimer() {
    localStorage.setItem(
        DEMO_DISCLAIMER_ACKNOWLEDGED_LOCAL_STORAGE_KEY,
        "true",
    );
    isDemoDisclaimerVisible.value = false;
}
</script>

<template>
    <Dialog
        v-model:visible="isDemoDisclaimerVisible"
        :modal="true"
        :closable="false"
        :dismissable-mask="false"
        :header="$gettext('Demo Site Disclaimer')"
        class="demo-disclaimer-dialog"
    >
        <p class="dialog-text">
            {{
                $gettext(
                    "This is a placeholder disclaimer for the Arches Lingo demo site. Replace this text with the final disclaimer copy before sharing this environment.",
                )
            }}
        </p>

        <template #footer>
            <Button
                :label="$gettext('I Understand')"
                @click="acknowledgeDemoDisclaimer"
            />
        </template>
    </Dialog>
</template>

<style scoped>
.demo-disclaimer-dialog {
    width: 34rem;
}

.dialog-text {
    margin: 0;
    font-size: var(--p-lingo-font-size-normal);
}
</style>
