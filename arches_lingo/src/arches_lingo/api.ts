import arches from "arches";
import Cookies from "js-cookie";
import { generateArchesURL } from "@/arches/utils/generate-arches-url.ts";

import type { Language } from "@/arches_component_lab/types";
import type {
    AdvancedSearchQuery,
    AdvancedSearchResponse,
    AdvancedSearchOptions,
    AppSettings,
    ConceptInstance,
    ConceptSetDetail,
    ConceptSetItem,
    DigitalObjectInstance,
    EditLogEntry,
    PaginatedResourceListResponse,
    SavedSearchItem,
    Scheme,
    SchemeInstance,
    TileData,
    User,
} from "@/arches_lingo/types";
import type {
    MissingTranslationsResponse,
    DashboardStats,
} from "@/arches_lingo/types/dashboard.ts";

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

export const fetchAppSettings = async (): Promise<AppSettings> => {
    const response = await fetch(
        generateArchesURL("arches_lingo:api-lingo-settings"),
    );
    const parsed = await response.json();
    if (!response.ok) throw new Error(parsed.message || response.statusText);
    return parsed;
};

export const fetchUser = async (): Promise<User> => {
    const response = await fetch(
        generateArchesURL("arches_lingo:api-lingo-user"),
    );
    const parsed = await response.json();
    if (!response.ok) throw new Error(parsed.message || response.statusText);
    return parsed;
};

export const fetchUserProfile = async (): Promise<User> => {
    const response = await fetch(
        generateArchesURL("arches_lingo:api-lingo-user-profile"),
    );
    const parsed = await response.json();
    if (!response.ok) throw new Error(parsed.message || response.statusText);
    return parsed;
};

export const updateUserProfile = async (
    profile: Pick<User, "first_name" | "last_name" | "email"> & {
        phone?: string;
    },
): Promise<User> => {
    const response = await fetch(
        generateArchesURL("arches_lingo:api-lingo-user-profile"),
        {
            method: "PUT",
            headers: {
                "X-CSRFTOKEN": getToken(),
                "Content-Type": "application/json",
            },
            body: JSON.stringify(profile),
        },
    );
    const parsed = await response.json();
    if (!response.ok) throw new Error(parsed.message || response.statusText);
    return parsed;
};

export const changePassword = async (
    oldPassword: string,
    newPassword: string,
    newPassword2: string,
): Promise<{ success: string }> => {
    const response = await fetch(
        generateArchesURL("arches_lingo:api-lingo-change-password"),
        {
            method: "POST",
            headers: {
                "X-CSRFTOKEN": getToken(),
                "Content-Type": "application/json",
            },
            body: JSON.stringify({
                old_password: oldPassword,
                new_password: newPassword,
                new_password2: newPassword2,
            }),
        },
    );
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

export const fetchSources = async (
    search: string = "",
    limit: number = 25,
    offset: number = 0,
): Promise<PaginatedResourceListResponse> => {
    const params = new URLSearchParams({
        limit: String(limit),
        offset: String(offset),
    });
    if (search) {
        params.set("search", search);
    }
    const response = await fetch(
        `${generateArchesURL("arches_lingo:api-lingo-sources")}?${params}`,
    );
    const parsed = await response.json();
    if (!response.ok) throw new Error(parsed.message || response.statusText);
    return parsed;
};

export const fetchContributors = async (
    search: string = "",
    limit: number = 25,
    offset: number = 0,
): Promise<PaginatedResourceListResponse> => {
    const params = new URLSearchParams({
        limit: String(limit),
        offset: String(offset),
    });
    if (search) {
        params.set("search", search);
    }
    const response = await fetch(
        `${generateArchesURL("arches_lingo:api-lingo-contributors")}?${params}`,
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
    if (!response.ok)
        throw new Error(
            parsed.message || parsed.content || response.statusText,
        );
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

export const fetchResourceReferenceCount = async (
    resourceId: string,
): Promise<number> => {
    const url = generateArchesURL(
        "arches_lingo:api-lingo-resource-reference-count",
        { resourceid: resourceId },
    );
    const response = await fetch(url);
    const parsed = await response.json();
    if (!response.ok) throw new Error(parsed.message || response.statusText);
    return parsed.count;
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
    if (!response.ok)
        throw new Error(
            parsed.message || parsed.content || response.statusText,
        );
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
    exclude: string[] = [],
    conceptIds: string[] = [],
) => {
    const params = new URLSearchParams({
        term: searchTerm,
        scheme: schemeResource,
        exclude: exclude?.join(","),
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

export const fetchConceptResource = async (conceptId: string) => {
    const parsed = await fetchConceptResources("", 1, 1, undefined, undefined, [
        conceptId,
    ]);
    return parsed.data[0];
};

export const fetchSchemeResource = async (schemeId: string) => {
    const url = generateArchesURL("arches_lingo:api-lingo-scheme", {
        pk: schemeId,
    });
    const response = await fetch(url);
    const parsed = await response.json();
    if (!response.ok) throw new Error(parsed.message || response.statusText);
    return parsed;
};

export const fetchSchemeTopConcepts = async (
    schemeId: string,
): Promise<Scheme> => {
    const baseUrl = generateArchesURL("arches_lingo:api-lingo-scheme", {
        pk: schemeId,
    });
    const url = `${baseUrl}?include_top_concepts=true`;
    const response = await fetch(url);
    const parsed = await response.json();
    if (!response.ok) throw new Error(parsed.message || response.statusText);
    return parsed;
};

export const fetchSchemeLabelCounts = async (schemeId: string) => {
    const url = generateArchesURL(
        "arches_lingo:api-lingo-scheme-label-counts",
        {
            pk: schemeId,
        },
    );
    const response = await fetch(url);
    const parsed = await response.json();
    if (!response.ok) throw new Error(parsed.message || response.statusText);
    return parsed;
};

export const fetchConceptRelationships = async (conceptId: string) => {
    const params = new URLSearchParams({
        concept: conceptId,
    });

    const url = `${generateArchesURL("arches_lingo:api-lingo-concept-relationships")}?${params.toString()}`;
    const response = await fetch(url);
    const parsed = await response.json();
    if (!response.ok) throw new Error(parsed.message || response.statusText);
    return parsed;
};

export const fetchLanguages = async () => {
    const url = generateArchesURL("arches:language");
    const response = await fetch(url);
    const parsed = await response.json();
    if (!response.ok) throw new Error(parsed.message || response.statusText);
    return parsed.languages as Language[];
};

export const fetchI18nData = async (languageCode?: string) => {
    const url = generateArchesURL("arches:get_frontend_i18n_data");
    const headers: Record<string, string> = {};
    if (languageCode) {
        headers["Accept-Language"] = languageCode;
    }
    const response = await fetch(url, { headers });
    const parsed = await response.json();
    if (!response.ok) throw new Error(parsed.message || response.statusText);
    return parsed as {
        enabled_languages: Record<string, string>;
        translations: Record<string, Record<string, string | string[]>>;
        language: string;
    };
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
    const formData = new FormData();
    formData.append("dismissals", JSON.stringify(notificationIds));
    const url = arches.urls.dismiss_notifications;
    const response = await fetch(url, {
        method: "POST",
        headers: { "X-CSRFTOKEN": getToken() },
        body: formData,
    });
    const parsed = await response.json();
    if (!response.ok) throw new Error(parsed.message || response.statusText);
    return parsed;
};

export const fetchResourceEditLog = async (
    resourceId: string,
): Promise<{ resourceid: string; edits: EditLogEntry[] }> => {
    const url = generateArchesURL("arches_lingo:api-lingo-edit-log", {
        resourceid: resourceId,
    });
    const response = await fetch(url);
    const parsed = await response.json();
    if (!response.ok) throw new Error(parsed.message || response.statusText);
    return parsed;
};

export const revertResourceToTimestamp = async (
    resourceId: string,
    timestamp: string,
): Promise<{
    status: "ok" | "partial_success";
    message: string;
    errors?: string[];
}> => {
    const url = generateArchesURL("arches_lingo:api-lingo-edit-log", {
        resourceid: resourceId,
    });
    const response = await fetch(url, {
        method: "POST",
        headers: {
            "X-CSRFTOKEN": getToken(),
            "Content-Type": "application/json",
        },
        body: JSON.stringify({ timestamp }),
    });
    const parsed = await response.json();
    if (!response.ok) throw new Error(parsed.message || response.statusText);
    return parsed;
};

export const getSearchExportFile = async (exportId: string) => {
    const params = new URLSearchParams({
        exportid: exportId,
    });
    const url = `${arches.urls.get_export_file}?${params.toString()}`;
    const response = await fetch(url);
    const parsed = await response.json();
    if (!response.ok) throw new Error(parsed.message || response.statusText);
    return parsed;
};

export const fetchResourceIdentifiers = async (resourceId: string) => {
    const url = generateArchesURL("arches:api-resource-identifiers", {
        resourceid: resourceId,
    });

    const response = await fetch(url);
    const parsed = await response.json();
    if (!response.ok) throw new Error(parsed.message || response.statusText);
    return parsed;
};

export const upsertResourceIdentifier = async (
    resourceId: string,
    resourceIdentifier: {
        id?: number;
        identifier: string;
        source: string;
        identifier_type?: string;
    },
) => {
    const url = generateArchesURL("arches:api-resource-identifiers", {
        resourceid: resourceId,
    });

    const response = await fetch(url, {
        method: "POST",
        headers: {
            "X-CSRFTOKEN": getToken(),
            "Content-Type": "application/json",
        },
        body: JSON.stringify(resourceIdentifier),
    });

    const parsed = await response.json();
    if (!response.ok) throw new Error(parsed.message || response.statusText);
    return parsed;
};

export const fetchConceptIdentifierCounter = async (
    schemeResourceInstanceId: string,
) => {
    const url = generateArchesURL(
        "arches_lingo:api-concept-identifier-counter",
        {
            scheme_resource_instance_id: schemeResourceInstanceId,
        },
    );

    const response = await fetch(url);
    const parsed = await response.json();
    if (!response.ok) throw new Error(parsed.message || response.statusText);
    return parsed;
};

export const createConceptIdentifierCounter = async (
    schemeResourceInstanceId: string,
    startNumber: number = 1,
) => {
    const url = generateArchesURL(
        "arches_lingo:api-concept-identifier-counter",
        {
            scheme_resource_instance_id: schemeResourceInstanceId,
        },
    );

    const response = await fetch(url, {
        method: "POST",
        headers: {
            "X-CSRFTOKEN": getToken(),
            "Content-Type": "application/json",
        },
        body: JSON.stringify({
            start_number: startNumber,
        }),
    });

    const parsed = await response.json();
    if (!response.ok) throw new Error(parsed.message || response.statusText);
    return parsed;
};

export const fetchResourceInstanceLifecycleStates = async () => {
    const resourceInstanceLifecycleStateUrl = generateArchesURL(
        "arches:api_resource_instance_lifecycle_states",
    );

    const response = await fetch(resourceInstanceLifecycleStateUrl);
    const parsedResponseBody = await response.json();
    if (!response.ok) {
        throw new Error(parsedResponseBody.message || response.statusText);
    }
    return parsedResponseBody;
};

export const fetchResourceInstanceLifecycleState = async (
    resourceId: string,
) => {
    const resourceInstanceLifecycleStateUrl = generateArchesURL(
        "arches:api_resource_instance_lifecycle_state",
        {
            resourceid: resourceId,
        },
    );

    const response = await fetch(resourceInstanceLifecycleStateUrl);
    const parsedResponseBody = await response.json();
    if (!response.ok) {
        throw new Error(parsedResponseBody.message || response.statusText);
    }
    return parsedResponseBody;
};

export const updateResourceInstanceLifecycleState = async (
    resourceId: string,
    resourceInstanceLifecycleStateId: string,
) => {
    const resourceInstanceLifecycleStateUrl = generateArchesURL(
        "arches:api_resource_instance_lifecycle_state",
        {
            resourceid: resourceId,
        },
    );

    const response = await fetch(resourceInstanceLifecycleStateUrl, {
        method: "POST",
        headers: {
            "X-CSRFTOKEN": getToken(),
            "Content-Type": "application/json",
        },
        body: JSON.stringify(resourceInstanceLifecycleStateId),
    });

    const parsedResponseBody = await response.json();
    if (!response.ok) {
        throw new Error(parsedResponseBody.message || response.statusText);
    }
    return parsedResponseBody;
};

export const fetchSchemeURITemplate = async (
    schemeResourceInstanceId: string,
) => {
    const url = generateArchesURL("arches_lingo:api-scheme-url-template", {
        scheme_resource_instance_id: schemeResourceInstanceId,
    });

    const response = await fetch(url);
    const parsed = await response.json();
    if (!response.ok) throw new Error(parsed.message || response.statusText);
    return parsed;
};

export const upsertSchemeURITemplate = async (
    schemeResourceInstanceId: string,
    urlTemplate: string,
) => {
    const url = generateArchesURL("arches_lingo:api-scheme-url-template", {
        scheme_resource_instance_id: schemeResourceInstanceId,
    });

    const response = await fetch(url, {
        method: "POST",
        headers: {
            "X-CSRFTOKEN": getToken(),
            "Content-Type": "application/json",
        },
        body: JSON.stringify({
            url_template: urlTemplate,
        }),
    });

    const parsed = await response.json();
    if (!response.ok) throw new Error(parsed.message || response.statusText);
    return parsed;
};

export const executeAdvancedSearch = async (
    query: AdvancedSearchQuery,
    page: number = 1,
    items: number = 25,
): Promise<AdvancedSearchResponse> => {
    const url = generateArchesURL("arches_lingo:api-advanced-search");
    const response = await fetch(url, {
        method: "POST",
        headers: {
            "X-CSRFTOKEN": getToken(),
            "Content-Type": "application/json",
        },
        body: JSON.stringify({ query, page, items }),
    });
    const parsed = await response.json();
    if (!response.ok) throw new Error(parsed.message || response.statusText);
    return parsed;
};

export const fetchAdvancedSearchOptions =
    async (): Promise<AdvancedSearchOptions> => {
        const url = generateArchesURL(
            "arches_lingo:api-advanced-search-options",
        );
        const response = await fetch(url);
        const parsed = await response.json();
        if (!response.ok)
            throw new Error(parsed.message || response.statusText);
        return parsed;
    };

export const fetchSavedSearches = async (): Promise<{
    data: SavedSearchItem[];
}> => {
    const url = generateArchesURL("arches_lingo:api-saved-searches");
    const response = await fetch(url);
    const parsed = await response.json();
    if (!response.ok) throw new Error(parsed.message || response.statusText);
    return parsed;
};

export const createSavedSearch = async (
    name: string,
    query: AdvancedSearchQuery,
): Promise<SavedSearchItem> => {
    const url = generateArchesURL("arches_lingo:api-saved-searches");
    const response = await fetch(url, {
        method: "POST",
        headers: {
            "X-CSRFTOKEN": getToken(),
            "Content-Type": "application/json",
        },
        body: JSON.stringify({ name, query }),
    });
    const parsed = await response.json();
    if (!response.ok) throw new Error(parsed.message || response.statusText);
    return parsed;
};

export const deleteSavedSearch = async (pk: number): Promise<void> => {
    const url = generateArchesURL("arches_lingo:api-saved-search-detail", {
        pk,
    });
    const response = await fetch(url, {
        method: "DELETE",
        headers: { "X-CSRFTOKEN": getToken() },
    });
    if (!response.ok) {
        const parsed = await response.json();
        throw new Error(parsed.message || response.statusText);
    }
};

export const fetchConceptSets = async (): Promise<{
    data: ConceptSetItem[];
}> => {
    const url = generateArchesURL("arches_lingo:api-concept-sets");
    const response = await fetch(url);
    const parsed = await response.json();
    if (!response.ok) throw new Error(parsed.message || response.statusText);
    return parsed;
};

export const createConceptSet = async (
    name: string,
    description: string = "",
): Promise<ConceptSetItem> => {
    const url = generateArchesURL("arches_lingo:api-concept-sets");
    const response = await fetch(url, {
        method: "POST",
        headers: {
            "X-CSRFTOKEN": getToken(),
            "Content-Type": "application/json",
        },
        body: JSON.stringify({ name, description }),
    });
    const parsed = await response.json();
    if (!response.ok) throw new Error(parsed.message || response.statusText);
    return parsed;
};

export const fetchConceptSetDetail = async (
    pk: number,
): Promise<ConceptSetDetail> => {
    const url = generateArchesURL("arches_lingo:api-concept-set-detail", {
        pk,
    });
    const response = await fetch(url);
    const parsed = await response.json();
    if (!response.ok) throw new Error(parsed.message || response.statusText);
    return parsed;
};

export const deleteConceptSet = async (pk: number): Promise<void> => {
    const url = generateArchesURL("arches_lingo:api-concept-set-detail", {
        pk,
    });
    const response = await fetch(url, {
        method: "DELETE",
        headers: { "X-CSRFTOKEN": getToken() },
    });
    if (!response.ok) {
        const parsed = await response.json();
        throw new Error(parsed.message || response.statusText);
    }
};

export const addToConceptSet = async (
    pk: number,
    conceptIds: string[],
): Promise<{ added: number; member_count: number }> => {
    const url = generateArchesURL("arches_lingo:api-concept-set-members", {
        pk,
    });
    const response = await fetch(url, {
        method: "POST",
        headers: {
            "X-CSRFTOKEN": getToken(),
            "Content-Type": "application/json",
        },
        body: JSON.stringify({ concept_ids: conceptIds }),
    });
    const parsed = await response.json();
    if (!response.ok) throw new Error(parsed.message || response.statusText);
    return parsed;
};

export const removeFromConceptSet = async (
    pk: number,
    conceptIds: string[],
): Promise<{ member_count: number }> => {
    const url = generateArchesURL("arches_lingo:api-concept-set-members", {
        pk,
    });
    const response = await fetch(url, {
        method: "DELETE",
        headers: {
            "X-CSRFTOKEN": getToken(),
            "Content-Type": "application/json",
        },
        body: JSON.stringify({ concept_ids: conceptIds }),
    });
    const parsed = await response.json();
    if (!response.ok) throw new Error(parsed.message || response.statusText);
    return parsed;
};

export const fetchDashboardStats = async (
    schemes?: string[],
    activityDays?: number,
): Promise<DashboardStats> => {
    const params = new URLSearchParams();
    if (schemes) {
        for (const scheme of schemes) {
            params.append("scheme", scheme);
        }
    }
    if (activityDays !== undefined) {
        params.append("days", String(activityDays));
    }
    const url = `${generateArchesURL("arches_lingo:api-lingo-dashboard")}?${params.toString()}`;
    const response = await fetch(url);
    const parsed = await response.json();
    if (!response.ok) throw new Error(parsed.message || response.statusText);
    return parsed;
};

export const fetchMissingTranslations = async (
    language: string,
    schemes?: string[],
    page = 1,
    items = 25,
): Promise<MissingTranslationsResponse> => {
    const params = new URLSearchParams({
        language,
        page: page.toString(),
        items: items.toString(),
    });
    if (schemes) {
        for (const scheme of schemes) {
            params.append("scheme", scheme);
        }
    }
    const url = `${generateArchesURL("arches_lingo:api-lingo-missing-translations")}?${params.toString()}`;
    const response = await fetch(url);
    const parsed = await response.json();
    if (!response.ok) throw new Error(parsed.message || response.statusText);
    return parsed;
};
