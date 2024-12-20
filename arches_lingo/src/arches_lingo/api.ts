import arches from "arches";
import Cookies from "js-cookie";
import type { SchemeInstance } from "@/arches_lingo/types";

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

export const fetchSchemeNamespace = async (schemeId: string) => {
    const response = await fetch(arches.urls.api_uri_namespace(schemeId));
    const parsed = await response.json();
    if (!response.ok) throw new Error(parsed.message || response.statusText);
    return parsed;
};

export const fetchTextualWorkRdmSystemList = async () => {
    const response = await fetch(arches.urls.api_textualwork_list);
    const parsed = await response.json();
    if (!response.ok) throw new Error(parsed.message || response.statusText);
    return parsed;
};

export const fetchSchemeCreation = async (schemeId: string) => {
    const response = await fetch(arches.urls.api_scheme_creation(schemeId));
    const parsed = await response.json();
    if (!response.ok) throw new Error(parsed.message || response.statusText);
    return parsed;
};

export const fetchSchemeLabel = async (schemeId: string) => {
    const response = await fetch(arches.urls.api_scheme_label(schemeId));
    const parsed = await response.json();
    if (!response.ok) throw new Error(parsed.message || response.statusText);
    return parsed;
};

export const deleteSchemeLabelTile = async (tileId: string) => {
    const response = await fetch(arches.urls.api_scheme_label_tile(tileId), {
        method: "DELETE",
        headers: { "X-CSRFTOKEN": getToken() },
    });

    if (!response.ok) {
        const parsed = await response.json();
        throw new Error(parsed.message || response.statusText);
    } else {
        return true;
    }
};

export const updateSchemeCreation = async (
    schemeId: string,
    schemeInstance: SchemeInstance,
) => {
    const response = await fetch(arches.urls.api_scheme_creation(schemeId), {
        method: "PATCH",
        headers: {
            "X-CSRFTOKEN": getToken(),
            "Content-Type": "application/json",
        },
        body: JSON.stringify(schemeInstance),
    });
    const parsed = await response.json();
    if (!response.ok) throw new Error(parsed.message || response.statusText);
    return parsed;
};

export const updateSchemeNamespace = async (
    schemeId: string,
    schemeNamespace: SchemeInstance,
) => {
    const response = await fetch(arches.urls.api_uri_namespace(schemeId), {
        method: "PATCH",
        headers: {
            "X-CSRFTOKEN": getToken(),
            "Content-Type": "application/json",
        },
        body: JSON.stringify(schemeNamespace),
    });
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

export const fetchSchemes = async () => {
    const response = await fetch(arches.urls.api_schemes);
    const parsed = await response.json();
    if (!response.ok) throw new Error(parsed.message || response.statusText);
    return parsed;
};
