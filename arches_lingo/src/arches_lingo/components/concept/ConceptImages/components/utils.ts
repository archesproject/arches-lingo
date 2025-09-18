import { fetchCardXNodeXWidgetData } from "@/arches_component_lab/generics/GenericWidget/api.ts";
import {
    createLingoResource,
    createLingoResourceFromForm,
    fetchLingoResourcePartial,
    updateLingoResource,
} from "@/arches_lingo/api.ts";
import { DIGITAL_OBJECT_GRAPH_SLUG } from "@/arches_lingo/components/concept/ConceptImages/components/constants.ts";
import { type Ref, toRaw } from "vue";
import type {
    ConceptInstance,
    DigitalObjectInstance,
    DigitalObjectInstanceAliases,
} from "@/arches_lingo/types.ts";

export async function createDigitalObject(
    digitalObjectData: DigitalObjectInstanceAliases | FormData,
): Promise<DigitalObjectInstance> {
    let digitalObjectResource;

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
    return digitalObjectResource as DigitalObjectInstance;
}

export async function addDigitalObjectToConceptImageCollection(
    digitalObjectResource: DigitalObjectInstance,
    conceptGraphSlug: string,
    conceptDigitalObjectRelationshipNodegroupAlias: string,
    conceptResourceInstanceId?: string,
) {
    if (conceptResourceInstanceId && digitalObjectResource.resourceinstanceid) {
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
                        },
                    },
                };
        }

        if (
            !conceptDigitalObjectRelationshipList?.aliased_data
                .depicting_digital_asset_internal?.aliased_data
                .depicting_digital_asset_internal.node_value
        ) {
            conceptDigitalObjectRelationshipList.aliased_data.depicting_digital_asset_internal.aliased_data.depicting_digital_asset_internal.node_value =
                [];
        }
        conceptDigitalObjectRelationshipList.aliased_data.depicting_digital_asset_internal.aliased_data.depicting_digital_asset_internal.node_value.push(
            {
                display_value: digitalObjectResource.display_value!,
                resourceId: digitalObjectResource.resourceinstanceid,
            },
        );
        await updateLingoResource(
            conceptGraphSlug,
            conceptResourceInstanceId,
            conceptDigitalObjectRelationshipList,
        );
    }
}

export async function createFormDataForFileUpload(
    resource: Ref<DigitalObjectInstance>,
    digitalObjectInstanceAliases: DigitalObjectInstanceAliases,
    // eslint-disable-next-line
    submittedFormData: { [k: string]: any },
): Promise<FormData> {
    const formData = new FormData();

    const cardXNodeXWidgetData = await fetchCardXNodeXWidgetData(
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
    for (const file of submittedFormData.content.node_value) {
        formData.append(`file-list_${digitalObjectContentNodeId}`, file.file);
    }
    return formData;
}
