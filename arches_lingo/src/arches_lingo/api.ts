import arches from "arches";
import Cookies from "js-cookie";
import type {
    AppellativeStatus,
    SchemeInstance,
    SchemeStatement,
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

export const fetchGroupRdmSystemList = async () => {
    const response = await fetch(arches.urls.api_group_list);
    const parsed = await response.json();
    if (!response.ok) throw new Error(parsed.message || response.statusText);
    return parsed;
};

export const fetchPersonRdmSystemList = async () => {
    const response = await fetch(arches.urls.api_person_list);
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

export const createSchemeLabel = async (
    schemeId: string,
    appellative_status: AppellativeStatus,
) => {
    const response = await fetch(arches.urls.api_scheme_label_list_create, {
        method: "POST",
        headers: {
            "X-CSRFTOKEN": getToken(),
            "Content-Type": "application/json",
        },
        body: JSON.stringify({
            resourceinstance: schemeId,
            ...appellative_status,
        }),
    });
    const parsed = await response.json();
    if (!response.ok) throw new Error(parsed.message || response.statusText);
    return parsed;
};

export const createSchemeNote = async (
    schemeId: string,
    statement: SchemeStatement,
) => {
    const response = await fetch(arches.urls.api_scheme_note_create, {
        method: "POST",
        headers: {
            "X-CSRFTOKEN": getToken(),
            "Content-Type": "application/json",
        },
        body: JSON.stringify({
            resourceinstance: schemeId,
            ...statement,
        }),
    });
    const parsed = await response.json();
    if (!response.ok) throw new Error(parsed.message || response.statusText);
    return parsed;
};

export const deleteSchemeLabelTile = async (
    schemeId: string,
    tileId: string,
) => {
    const response = await fetch(
        arches.urls.api_scheme_label_tile(schemeId, tileId),
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

export const updateSchemeLabel = async (
    schemeId: string,
    tileId: string,
    appellative_status: AppellativeStatus,
) => {
    const response = await fetch(
        arches.urls.api_scheme_label_tile(schemeId, tileId),
        {
            method: "PATCH",
            headers: {
                "X-CSRFTOKEN": getToken(),
                "Content-Type": "application/json",
            },
            body: JSON.stringify(appellative_status),
        },
    );
    const parsed = await response.json();
    if (!response.ok)
        throw new Error(
            parsed.non_field_errors || parsed.message || response.statusText,
        );
    return parsed;
};

export const fetchSchemeNotes = async (schemeId: string) => {
    const response = await fetch(arches.urls.api_scheme_note(schemeId));
    const parsed = await response.json();
    if (!response.ok) throw new Error(parsed.message || response.statusText);
    return parsed;
};

export const updateSchemeNote = async (
    schemeId: string,
    tileId: string,
    schemeStatement: SchemeStatement,
) => {
    const response = await fetch(
        arches.urls.api_scheme_note_tile(schemeId, tileId),
        {
            method: "PATCH",
            headers: {
                "X-CSRFTOKEN": getToken(),
                "Content-Type": "application/json",
            },
            body: JSON.stringify(schemeStatement),
        },
    );
    const parsed = await response.json();
    if (!response.ok) throw new Error(parsed.message || response.statusText);
    return parsed;
};

export const deleteSchemeNoteTile = async (
    schemeId: string,
    tileId: string,
) => {
    const response = await fetch(
        arches.urls.api_scheme_note_tile(schemeId, tileId),
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
    const response = await fetch(arches.urls.api_schemes, {
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

export const fetchSchemeRights = async (schemeId: string) => {
    const response = await fetch(arches.urls.api_scheme_rights(schemeId));
    const parsed = await response.json();
    if (!response.ok) throw new Error(parsed.message || response.statusText);
    return parsed;
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

export const updateSchemeRights = async (
    schemeId: string,
    schemeRights: SchemeInstance,
) => {
    const response = await fetch(arches.urls.api_scheme_rights(schemeId), {
        method: "PATCH",
        headers: {
            "X-CSRFTOKEN": getToken(),
            "Content-Type": "application/json",
        },
        body: JSON.stringify(schemeRights),
    });
    const parsed = await response.json();
    console.log(parsed);
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

export const fetchControlledListOptions = async (controlledListId: string) => {
    const response = await fetch(arches.urls.controlled_list(controlledListId));
    const parsed = await response.json();
    if (!response.ok) throw new Error(parsed.message || response.statusText);
    return parsed;
};
