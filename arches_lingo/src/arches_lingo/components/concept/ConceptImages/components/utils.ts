import arches from "arches";

import { useWidgetConfigStore } from "@/arches_vue_components/stores/useWidgetConfigStore.ts";
import {
    createLingoResource,
    createLingoResourceFromForm,
    fetchLingoResourcePartial,
    updateLingoResource,
} from "@/arches_lingo/api.ts";
import { DIGITAL_OBJECT_GRAPH_SLUG } from "@/arches_lingo/components/concept/ConceptImages/components/constants.ts";
import { type Ref, toRaw } from "vue";
import type { FileListAliasedNodeData } from "@/arches_vue_components/datatypes/file-list/types.ts";
import type { ResourceInstanceListAliasedNodeData } from "@/arches_vue_components/datatypes/resource-instance-list/types.ts";
import type {
    ConceptInstance,
    DigitalObjectInstance,
    DigitalObjectInstanceAliases,
} from "@/arches_lingo/types.ts";

export function getFileUrl(originalUrl: string): string {
    const httpRegex = /^(blob:|https?:\/\/)/;
    if (
        !originalUrl ||
        httpRegex.test(originalUrl) ||
        originalUrl.startsWith(arches.urls.url_subpath)
    ) {
        return originalUrl;
    }
    return (arches.urls.url_subpath + originalUrl).replace("//", "/");
}

function getDigitalObjectFileReference(resource: DigitalObjectInstance) {
    const contentData = resource.aliased_data.content?.aliased_data
        .content as unknown as FileListAliasedNodeData | undefined;
    return contentData?.node_value?.[0];
}

export function getDigitalObjectImageUrl(
    resource: DigitalObjectInstance,
): string | undefined {
    const fileReference = getDigitalObjectFileReference(resource);
    return fileReference?.url ? getFileUrl(fileReference.url) : undefined;
}

export function getDigitalObjectImageAlt(
    resource: DigitalObjectInstance,
): string {
    const fileReference = getDigitalObjectFileReference(resource);
    return fileReference?.altText || fileReference?.name || "";
}

export async function createDigitalObject(
    digitalObjectData: DigitalObjectInstanceAliases | FormData,
): Promise<DigitalObjectInstance> {
    let digitalObjectResource: DigitalObjectInstance;

    if (digitalObjectData instanceof FormData) {
        digitalObjectResource = await createLingoResourceFromForm(
            digitalObjectData,
            DIGITAL_OBJECT_GRAPH_SLUG,
        );
    } else {
        digitalObjectResource = await createLingoResource(
            {
                aliased_data: digitalObjectData,
            } as DigitalObjectInstance,
            DIGITAL_OBJECT_GRAPH_SLUG,
        );
    }
    return digitalObjectResource;
}

export async function addDigitalObjectToConceptImageCollection(
    digitalObjectResource: DigitalObjectInstance,
    conceptGraphSlug: string,
    conceptDigitalObjectRelationshipNodegroupAlias: string,
    conceptResourceInstanceId?: string,
) {
    if (
        !conceptResourceInstanceId ||
        !digitalObjectResource.resourceinstanceid
    ) {
        return;
    }

    const conceptDigitalObjectRelationshipList =
        (await fetchLingoResourcePartial(
            conceptGraphSlug,
            conceptResourceInstanceId,
            conceptDigitalObjectRelationshipNodegroupAlias,
        )) as ConceptInstance;

    if (
        !conceptDigitalObjectRelationshipList.aliased_data
            .depicting_digital_asset_internal
    ) {
        conceptDigitalObjectRelationshipList.aliased_data.depicting_digital_asset_internal =
            {
                aliased_data: {
                    depicting_digital_asset_internal: {
                        display_value: "",
                        node_value: [],
                        details: [],
                    } as ResourceInstanceListAliasedNodeData,
                },
            };
    }

    const depictingNodeData =
        conceptDigitalObjectRelationshipList.aliased_data
            .depicting_digital_asset_internal.aliased_data
            .depicting_digital_asset_internal;

    depictingNodeData.node_value = [
        ...(depictingNodeData.node_value ?? []),
        {
            resourceId: digitalObjectResource.resourceinstanceid,
            ontologyProperty: "",
            inverseOntologyProperty: "",
            resourceXresourceId: "",
        },
    ];

    await updateLingoResource(
        conceptGraphSlug,
        conceptResourceInstanceId,
        conceptDigitalObjectRelationshipList,
    );
}

export async function createFormDataForFileUpload(
    resource: Ref<DigitalObjectInstance>,
    digitalObjectInstanceAliases: DigitalObjectInstanceAliases,
    // eslint-disable-next-line
    submittedFormData: { [k: string]: any },
): Promise<FormData> {
    const formData = new FormData();

    const cardXNodeXWidgetData = await useWidgetConfigStore().fetchWidgetConfig(
        DIGITAL_OBJECT_GRAPH_SLUG,
        "content",
    );
    const digitalObjectContentNodeId = cardXNodeXWidgetData.node.nodeid;
    const val = toRaw(resource.value);
    if (resource.value) {
        formData.append("json", JSON.stringify(val));
    } else {
        formData.append(
            "json",
            new Blob([JSON.stringify(digitalObjectInstanceAliases)], {
                type: "application/json",
            }),
        );
    }
    for (const file of (submittedFormData.content as Array<{ file?: File }>) ??
        []) {
        if (file.file instanceof File) {
            const sanitizedName = file.file.name.replace(/ /g, "_");
            formData.append(
                `file-list_${digitalObjectContentNodeId}`,
                file.file,
                sanitizedName,
            );
        }
    }
    return formData;
}
