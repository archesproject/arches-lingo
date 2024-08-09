import arches from "arches";
import Cookies from "js-cookie";

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
    try {
        const parsed = await response.json();
        if (response.ok) {
            return parsed;
        }
        throw new Error(parsed.message);
    } catch (error) {
        throw new Error((error as Error).message || response.statusText);
    }
};

export const logout = async () => {
    const response = await fetch(arches.urls.api_logout, {
        method: "POST",
        headers: { "X-CSRFTOKEN": getToken() },
    });
    if (response.ok) {
        return true;
    }
    try {
        const error = await response.json();
        throw new Error(error.message);
    } catch (error) {
        throw new Error((error as Error).message || response.statusText);
    }
};
