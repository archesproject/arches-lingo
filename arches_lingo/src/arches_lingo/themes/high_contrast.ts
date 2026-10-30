export const HIGH_CONTRAST_CLASS = "arches-high-contrast";

const HIGH_CONTRAST_STORAGE_KEY = `arches.${HIGH_CONTRAST_CLASS}`;
const PREFERS_MORE_CONTRAST_QUERY = "(prefers-contrast: more)";

export function isHighContrastPreferred(): boolean {
    const storedPreference = localStorage.getItem(HIGH_CONTRAST_STORAGE_KEY);

    if (storedPreference === null) {
        return window.matchMedia(PREFERS_MORE_CONTRAST_QUERY).matches;
    }
    return storedPreference === "true";
}

export function applyHighContrast(isEnabled: boolean) {
    document.documentElement.classList.toggle(HIGH_CONTRAST_CLASS, isEnabled);
}

export function setHighContrast(isEnabled: boolean) {
    applyHighContrast(isEnabled);
    localStorage.setItem(HIGH_CONTRAST_STORAGE_KEY, isEnabled.toString());
}
