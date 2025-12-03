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
