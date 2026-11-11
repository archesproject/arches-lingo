import { computed, toValue } from "vue";
import type { MaybeRefOrGetter } from "vue";

import { storeToRefs } from "pinia";
import { useGettext } from "vue3-gettext";

import { useCopyToClipboard } from "@/arches_lingo/composables/useCopyToClipboard.ts";
import { useAppSettingsStore } from "@/arches_lingo/stores/useAppSettingsStore.ts";

// Scheme services are routed by Django's slug converter, so a scheme whose
// identifier is not a slug is offered the global service instead.
const SLUG_PATTERN = /^[-a-zA-Z0-9_]+$/;

export function useReconciliationService(
    schemeIdentifier: MaybeRefOrGetter<string | undefined> = undefined,
    schemeName: MaybeRefOrGetter<string | undefined> = undefined,
) {
    const { $gettext, interpolate } = useGettext();
    const { copyToClipboard } = useCopyToClipboard();
    const {
        reconciliationEnabled,
        reconciliationServiceUrl,
        schemeReconciliationServiceUrlTemplate,
    } = storeToRefs(useAppSettingsStore());

    const schemeServiceUrl = computed(() => {
        const identifier = toValue(schemeIdentifier);
        if (
            !identifier ||
            !SLUG_PATTERN.test(identifier) ||
            !schemeReconciliationServiceUrlTemplate.value
        ) {
            return undefined;
        }
        return schemeReconciliationServiceUrlTemplate.value.replace(
            "{scheme_identifier}",
            identifier,
        );
    });

    const serviceUrl = computed(
        () => schemeServiceUrl.value ?? reconciliationServiceUrl.value,
    );

    const isServiceAvailable = computed(() =>
        Boolean(reconciliationEnabled.value && serviceUrl.value),
    );

    const usageHint = computed(() => {
        if (schemeServiceUrl.value) {
            return $gettext(
                "Add this URL as a standard reconciliation service in OpenRefine to match spreadsheet values against this scheme.",
            );
        }
        const name = toValue(schemeName);
        if (name) {
            return interpolate(
                $gettext(
                    'Add this URL as a standard reconciliation service in OpenRefine, then choose "%{scheme}" as the type to reconcile against.',
                ),
                { scheme: name },
                true,
            );
        }
        return $gettext(
            "Add this URL as a standard reconciliation service in OpenRefine to match spreadsheet values against published schemes.",
        );
    });

    async function copyServiceUrl(): Promise<void> {
        await copyToClipboard(serviceUrl.value ?? "", {
            copiedSummary: $gettext(
                "Reconciliation service URL copied to clipboard",
            ),
            failedSummary: $gettext(
                "Unable to copy the reconciliation service URL",
            ),
        });
    }

    return { isServiceAvailable, serviceUrl, usageHint, copyServiceUrl };
}
