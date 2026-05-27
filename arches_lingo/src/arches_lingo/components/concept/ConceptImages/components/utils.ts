import { useWidgetConfigStore } from "@/arches_component_lab/stores/useWidgetConfigStore.ts";
import {
    createLingoResource,
    createLingoResourceFromForm,
    fetchLingoResourcePartial,
    updateLingoResource,
} from "@/arches_lingo/api.ts";
import { DIGITAL_OBJECT_GRAPH_SLUG } from "@/arches_lingo/components/concept/ConceptImages/components/constants.ts";
import { type Ref, toRaw } from "vue";
import type { ResourceInstanceListAliasedNodeData } from "@/arches_component_lab/datatypes/resource-instance-list/types.ts";
import type {
    ConceptInstance,
    DigitalObjectInstance,
    DigitalObjectInstanceAliases,
} from "@/arches_lingo/types.ts";

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
        if (file.file) {
            formData.append(
                `file-list_${digitalObjectContentNodeId}`,
                file.file,
            );
        }
    }
    return formData;
}
