import arches from "arches";
import Cookies from "js-cookie";
import { generateArchesURL } from "@/arches/utils/generate-arches-url.ts";

import type {
    ConceptInstance,
    DigitalObjectInstance,
    SchemeInstance,
    TileData,
} from "@/arches_lingo/types";

function getToken() {
    const token = Cookies.get("csrftoken");
    if (!token) {
        throw new Error("Missing csrftoken");
    }
    return token;
}

export const login = async (username: string, password: string) => {
    const response = await fetch(arches.urls.api_login, {
        method: "POST",
        headers: { "X-CSRFTOKEN": getToken() },
        body: JSON.stringify({ username, password }),
    });
    const parsed = await response.json();
    if (!response.ok) throw new Error(parsed.message || response.statusText);
    return parsed;
};

export const logout = async () => {
    const response = await fetch(arches.urls.api_logout, {
        method: "POST",
        headers: { "X-CSRFTOKEN": getToken() },
    });
    if (response.ok) return true;
    const parsedError = await response.json();
    throw new Error(parsedError.message || response.statusText);
};

export const fetchUser = async () => {
    const response = await fetch(arches.urls.api_user);
    const parsed = await response.json();
    if (!response.ok) throw new Error(parsed.message || response.statusText);
    return parsed;
};

export const fetchLingoResources = async (graphSlug: string) => {
    const response = await fetch(arches.urls.api_lingo_resources(graphSlug));
    const parsed = await response.json();
    if (!response.ok) throw new Error(parsed.message || response.statusText);
    return parsed;
};

export const fetchLingoResource = async (
    graphSlug: string,
    resourceInstanceId: string,
) => {
    const response = await fetch(
        arches.urls.api_lingo_resource(graphSlug, resourceInstanceId),
    );
    const parsed = await response.json();
    if (!response.ok) throw new Error(parsed.message || response.statusText);
    return parsed;
};

export const fetchLingoResourcesBatch = async (
    graphSlug: string,
    resourceInstanceIds: string[],
) => {
    const params = {
        resource_ids: resourceInstanceIds.join(","),
    };

    const response = await fetch(
        `${arches.urls.api_lingo_resources(graphSlug)}?${new URLSearchParams(params)}`,
    );
    const parsed = await response.json();
    if (!response.ok) throw new Error(parsed.message || response.statusText);
    return parsed;
};

export const fetchLingoResourcePartial = async (
    graphSlug: string,
    resourceId: string,
    nodegroupAlias: string,
) => {
    const response = await fetch(
        arches.urls.api_lingo_resource_partial(
            graphSlug,
            resourceId,
            nodegroupAlias,
        ),
    );
    const parsed = await response.json();
    if (!response.ok) throw new Error(parsed.message || response.statusText);
    return parsed;
};

export const updateLingoResourceFromForm = async (
    graphSlug: string,
    resourceId: string,
    formData: FormData,
) => {
    const headers = {
        "X-CSRFTOKEN": getToken(),
    };
    const response = await fetch(
        arches.urls.api_lingo_resource(graphSlug, resourceId),
        {
            method: "PATCH",
            headers: headers,
            body: formData,
        },
    );
    const parsed = await response.json();
    if (!response.ok) throw new Error(parsed.message || response.statusText);
    return parsed;
};

export const updateLingoResource = async (
    graphSlug: string,
    resourceId: string,
    instance: SchemeInstance | ConceptInstance | DigitalObjectInstance,
) => {
    const headers = {
        "X-CSRFTOKEN": getToken(),
        "Content-Type": "application/json",
    };

    const response = await fetch(
        arches.urls.api_lingo_resource(graphSlug, resourceId),
        {
            method: "PATCH",
            headers: headers,
            body: JSON.stringify(instance),
        },
    );
    const parsed = await response.json();
    if (!response.ok) throw new Error(parsed.message || response.statusText);
    return parsed;
};

export const deleteLingoResource = async (
    graphSlug: string,
    resourceId: string,
) => {
    const response = await fetch(
        arches.urls.api_lingo_resource(graphSlug, resourceId),
        {
            method: "DELETE",
            headers: { "X-CSRFTOKEN": getToken() },
        },
    );
    if (!response.ok) {
        const parsed = await response.json();
        throw new Error(parsed.message || response.statusText);
    } else {
        return true;
    }
};

export const upsertLingoTile = async (
    graphSlug: string,
    nodegroupAlias: string,
    tileData: TileData,
) => {
    const url = tileData.tileid
        ? arches.urls.api_lingo_tile
        : arches.urls.api_lingo_tiles;
    const response = await fetch(
        url(graphSlug, nodegroupAlias, tileData.tileid),
        {
            method: tileData.tileid ? "PATCH" : "POST",
            headers: {
                "X-CSRFTOKEN": getToken(),
                "Content-Type": "application/json",
            },
            body: JSON.stringify(tileData),
        },
    );

    const parsed = await response.json();
    if (!response.ok)
        throw new Error(
            // TODO: show all errors
            parsed.non_field_errors || parsed.message || response.statusText,
        );
    return parsed;
};

export const deleteLingoTile = async (
    graphSlug: string,
    nodegroupAlias: string,
    tileId: string,
) => {
    const response = await fetch(
        arches.urls.api_lingo_tile(graphSlug, nodegroupAlias, tileId),
        {
            method: "DELETE",
            headers: { "X-CSRFTOKEN": getToken() },
        },
    );

    if (!response.ok) {
        const parsed = await response.json();
        throw new Error(parsed.message || response.statusText);
    } else {
        return true;
    }
};

export const createLingoResourceFromForm = async (
    newResource: FormData,
    graphSlug: string,
) => {
    const headers = {
        "X-CSRFTOKEN": getToken(),
    };

    const response = await fetch(arches.urls.api_lingo_resources(graphSlug), {
        method: "POST",
        headers: headers,
        body: newResource,
    });

    const parsed = await response.json();
    if (!response.ok) throw new Error(parsed.message || response.statusText);
    return parsed;
};

export const createLingoResource = async (
    newResource: SchemeInstance | ConceptInstance | DigitalObjectInstance,
    graphSlug: string,
) => {
    type headerType = {
        "X-CSRFTOKEN": string;
        "Content-Type"?: string;
    };
    const headers: headerType = {
        "X-CSRFTOKEN": getToken(),
    };

    headers["Content-Type"] = "application/json";

    const response = await fetch(arches.urls.api_lingo_resources(graphSlug), {
        method: "POST",
        headers: headers,
        body: JSON.stringify(newResource),
    });

    const parsed = await response.json();
    if (!response.ok) throw new Error(parsed.message || response.statusText);
    return parsed;
};

export const fetchSearchResults = async (
    searchTerm: string,
    items: number,
    page: number,
    orderMode: string = "unsorted",
) => {
    const params = new URLSearchParams({
        term: searchTerm,
        items: items.toString(),
        page: page.toString(),
        order: orderMode,
    });

    const url = `${arches.urls.api_search}?${params.toString()}`;
    const response = await fetch(url);
    const parsed = await response.json();
    if (!response.ok) throw new Error(parsed.message || response.statusText);
    return parsed;
};

export const fetchConceptResources = async (
    searchTerm: string,
    items: number,
    page: number,
    schemeResource: string = "",
    exclude: boolean = false,
    conceptIds: string[] = [],
) => {
    const params = new URLSearchParams({
        term: searchTerm,
        scheme: schemeResource,
        exclude: exclude.toString(),
        items: items.toString(),
        page: page.toString(),
        concepts: conceptIds.join(","),
    });

    const url = `${generateArchesURL("arches_lingo:api-lingo-concept-resources")}?${params.toString()}`;
    const response = await fetch(url);
    const parsed = await response.json();
    if (!response.ok) throw new Error(parsed.message || response.statusText);
    return parsed;
};

export const fetchConceptRelationships = async (
    conceptId: string,
    type: string,
) => {
    const params = new URLSearchParams({
        concept: conceptId,
        type: type,
    });

    const url = `${generateArchesURL("arches_lingo:api-lingo-concept-relationships")}?${params.toString()}`;
    const response = await fetch(url);
    const parsed = await response.json();
    if (!response.ok) throw new Error(parsed.message || response.statusText);
    return parsed;
};

export const fetchConcepts = async () => {
    const response = await fetch(arches.urls.api_concepts);
    const parsed = await response.json();
    if (!response.ok) throw new Error(parsed.message || response.statusText);
    return parsed;
};

export const fetchControlledListOptions = async (controlledListId: string) => {
    const response = await fetch(arches.urls.controlled_list(controlledListId));
    const parsed = await response.json();
    if (!response.ok) throw new Error(parsed.message || response.statusText);
    return parsed;
};

export const importThesaurus = async (file: File, overwriteOption: string) => {
    const formData = new FormData();
    formData.append("action", "start");
    formData.append("mode", "ui");
    // moduleId normally fetched in context of BDM, but needed to get throough ETLManagerView POST
    const lingoImporterModuleId = "11cad3ca-e155-44b1-9910-c50b3def47f6";
    formData.append("module", lingoImporterModuleId);

    // Mimic Bulk Data Manager behavior - 'Start' request initializes new load event
    const startResponse = await fetch(arches.urls.etl_manager, {
        method: "POST",
        headers: { "X-CSRFTOKEN": getToken() },
        body: formData,
    });

    if (startResponse.ok) {
        const parsed = await startResponse.json();
        const loadId = parsed.result.load_id;
        formData.append("load_id", loadId);
        formData.append("overwrite_option", overwriteOption);
        formData.append("file", file);
        formData.set("action", "write");
        // Subsequent 'Write' request to actually upload the file and start the import
        const response = await fetch(arches.urls.etl_manager, {
            method: "POST",
            headers: { "X-CSRFTOKEN": getToken() },
            body: formData,
        });

        try {
            const parsed = await response.json();
            if (response.ok) {
                return parsed;
            }
            throw new Error(parsed.message);
        } catch (error) {
            throw new Error((error as Error).message || response.statusText);
        }
    }
};

export const exportThesaurus = async (
    resourceid: string,
    format: string,
    fileName?: string,
) => {
    const formData = new FormData();
    formData.append("action", "start");
    // moduleId normally fetched in context of BDM, but needed to get throough ETLManagerView POST
    const lingoImporterModuleId = "4302e334-33ed-4e85-99f2-fdac7c7c32fa";
    formData.append("module", lingoImporterModuleId);
    formData.append("resourceid", resourceid);
    formData.append("format", format);
    if (fileName) {
        formData.append("filename", fileName);
    }
    const response = await fetch(arches.urls.etl_manager, {
        method: "POST",
        headers: { "X-CSRFTOKEN": getToken() },
        body: formData,
    });
    try {
        const parsed = await response.json();
        if (response.ok) {
            return parsed;
        }
        throw new Error(parsed.message || parsed.data?.message);
    } catch (error) {
        throw new Error((error as Error).message || response.statusText);
    }
};

export const fetchUserNotifications = async (
    items: number,
    page: number,
    unreadOnly: boolean,
) => {
    const params = new URLSearchParams({
        items: items.toString(),
        page: page.toString(),
    });
    if (unreadOnly) {
        params.append("unread_only", unreadOnly.toString());
    }
    const url = `${arches.urls.get_notifications}?${params.toString()}`;
    const response = await fetch(url);
    const parsed = await response.json();
    if (!response.ok) throw new Error(parsed.message || response.statusText);
    return parsed;
};

export const dismissNotifications = async (notificationIds: string[]) => {
    const params = new URLSearchParams({
        notification_ids: JSON.stringify(notificationIds),
    });
    const url = `${arches.urls.dismiss_notifications}?${params.toString()}`;
    const response = await fetch(url, {
        method: "POST",
        headers: { "X-CSRFTOKEN": getToken() },
    });
    const parsed = await response.json();
    if (!response.ok) throw new Error(parsed.message || response.statusText);
    return parsed;
};
