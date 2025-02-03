import arches from "arches";
import Cookies from "js-cookie";

import type {
    SchemeInstance,
    SchemeRights,
    SchemeRightStatement,
    SchemeTile,
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
    schemeId: string,
) => {
    const response = await fetch(
        arches.urls.api_lingo_resource(graphSlug, schemeId),
    );
    const parsed = await response.json();
    if (!response.ok) throw new Error(parsed.message || response.statusText);
    return parsed;
};

export const fetchLingoResourcePartial = async (
    graphSlug: string,
    schemeId: string,
    nodegroupAlias: string,
) => {
    const response = await fetch(
        arches.urls.api_lingo_resource_partial(
            graphSlug,
            schemeId,
            nodegroupAlias,
        ),
    );
    const parsed = await response.json();
    if (!response.ok) throw new Error(parsed.message || response.statusText);
    return parsed;
};

export const updateLingoResource = async (
    graphSlug: string,
    schemeId: string,
    schemeInstance: SchemeInstance,
) => {
    const response = await fetch(
        arches.urls.api_lingo_resource(graphSlug, schemeId),
        {
            method: "PATCH",
            headers: {
                "X-CSRFTOKEN": getToken(),
                "Content-Type": "application/json",
            },
            body: JSON.stringify(schemeInstance),
        },
    );
    const parsed = await response.json();
    if (!response.ok) throw new Error(parsed.message || response.statusText);
    return parsed;
};

export const upsertLingoTile = async (
    graphSlug: string,
    nodegroupAlias: string,
    tileData: SchemeTile, // TODO: generalize type
    tileId: string | undefined,
) => {
    const url = tileId
        ? arches.urls.api_lingo_tile
        : arches.urls.api_lingo_tiles;
    const response = await fetch(url(graphSlug, nodegroupAlias, tileId), {
        method: tileId ? "PATCH" : "POST",
        headers: {
            "X-CSRFTOKEN": getToken(),
            "Content-Type": "application/json",
        },
        body: JSON.stringify(tileData),
    });

    const parsed = await response.json();
    if (!response.ok)
        throw new Error(
            // TODO: show all errors
            parsed.non_field_errors || parsed.message || response.statusText,
        );
    return parsed;
};

export const deleteLingoTile = async (
    schemeId: string,
    nodegroupAlias: string,
    tileId: string,
) => {
    const response = await fetch(
        arches.urls.api_lingo_tile(schemeId, nodegroupAlias, tileId),
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

export const createScheme = async (newScheme: SchemeInstance) => {
    const response = await fetch(arches.urls.api_lingo_resources("scheme"), {
        method: "POST",
        headers: {
            "X-CSRFTOKEN": getToken(),
            "Content-Type": "application/json",
        },
        body: JSON.stringify(newScheme),
    });
    const parsed = await response.json();
    if (!response.ok) throw new Error(parsed.message || response.statusText);
    return parsed;
};

export const createSchemeFromRights = async (
    schemeRightsValue: SchemeInstance,
) => {
    const response = await fetch(arches.urls.api_scheme_rights_list_create, {
        method: "POST",
        headers: {
            "X-CSRFTOKEN": getToken(),
            "Content-Type": "application/json",
        },
        body: JSON.stringify({ schemeRightsValue }),
    });
    const parsed = await response.json();
    if (!response.ok) throw new Error(parsed.message || response.statusText);
    return parsed;
};

export const updateSchemeRights = async (
    schemeId: string,
    schemeRightsValue: SchemeRights,
    schemeRightStatementValue: SchemeRightStatement,
) => {
    const response = await fetch(
        arches.urls.api_scheme_rights_detail(schemeId),
        {
            method: "PATCH",
            headers: {
                "X-CSRFTOKEN": getToken(),
                "Content-Type": "application/json",
            },
            body: JSON.stringify({
                resourceinstanceid: schemeId,
                rights: schemeRightsValue,
                right_statement: schemeRightStatementValue,
            }),
        },
    );
    const parsed = await response.json();
    if (!response.ok) throw new Error(parsed.message || response.statusText);
    return parsed;
};

export const fetchSearchResults = async (
    searchTerm: string,
    items: number,
    page: number,
) => {
    const params = new URLSearchParams({
        term: searchTerm,
        items: items.toString(),
        page: page.toString(),
    });

    const url = `${arches.urls.api_search}?${params.toString()}`;
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
