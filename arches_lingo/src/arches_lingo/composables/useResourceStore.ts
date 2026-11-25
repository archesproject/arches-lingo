import { computed, provide, inject, ref, readonly } from "vue";

import {
    ResourceNotFoundError,
    fetchLingoResource,
    fetchLingoResourcePartial,
} from "@/arches_lingo/api.ts";

import type { Ref, InjectionKey } from "vue";
import type { ResourceInstanceResult } from "@/arches_lingo/types.ts";

export interface ResourceStore {
    resource: Readonly<Ref<ResourceInstanceResult | null>>;
    isLoading: Readonly<Ref<boolean>>;
    error: Readonly<Ref<Error | null>>;
    isNotFound: Readonly<Ref<boolean>>;
    initialLoad: Promise<void>;
    refreshNodegroup: (nodegroupAlias: string) => Promise<void>;
    refreshResource: () => Promise<void>;
}

export const RESOURCE_STORE_KEY = Symbol(
    "resourceStore",
) as InjectionKey<ResourceStore>;

export function createResourceStore(
    graphSlug: string,
    resourceInstanceId: string | undefined,
): ResourceStore {
    const resource = ref<ResourceInstanceResult | null>(null);
    const isLoading = ref(!!resourceInstanceId);
    const error = ref<Error | null>(null);
    const isNotFound = computed(
        () => error.value instanceof ResourceNotFoundError,
    );

    async function fetchFullResource() {
        if (!resourceInstanceId) {
            return;
        }
        isLoading.value = true;
        error.value = null;
        try {
            resource.value = await fetchLingoResource(
                graphSlug,
                resourceInstanceId,
            );
        } catch (err) {
            error.value = err as Error;
        } finally {
            isLoading.value = false;
        }
    }

    async function refreshNodegroup(nodegroupAlias: string) {
        if (!resourceInstanceId) return;
        try {
            const partial = await fetchLingoResourcePartial(
                graphSlug,
                resourceInstanceId,
                nodegroupAlias,
            );
            if (resource.value) {
                resource.value = {
                    ...resource.value,
                    aliased_data: {
                        ...resource.value.aliased_data,
                        [nodegroupAlias]: partial.aliased_data[nodegroupAlias],
                    },
                };
            }
        } catch {
            await fetchFullResource();
        }
    }

    async function refreshResource() {
        await fetchFullResource();
    }

    // Start initial fetch immediately
    const initialLoad = fetchFullResource();

    return {
        resource: readonly(resource) as Readonly<
            Ref<ResourceInstanceResult | null>
        >,
        isLoading: readonly(isLoading),
        error: readonly(error),
        isNotFound,
        initialLoad,
        refreshNodegroup,
        refreshResource,
    };
}

export function provideResourceStore(store: ResourceStore) {
    provide(RESOURCE_STORE_KEY, store);
}

export function useResourceStore(): ResourceStore {
    const store = inject(RESOURCE_STORE_KEY);
    if (!store) {
        throw new Error(
            "ResourceStore not provided. Ensure provideResourceStore() is called in a parent component.",
        );
    }
    return store;
}
