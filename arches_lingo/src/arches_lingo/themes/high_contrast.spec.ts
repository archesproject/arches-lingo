import { afterEach, describe, expect, it, vi } from "vitest";

import {
    HIGH_CONTRAST_CLASS,
    isHighContrastPreferred,
    setHighContrast,
} from "@/arches_lingo/themes/high_contrast.ts";

function stubPrefersMoreContrast(matches: boolean) {
    vi.stubGlobal(
        "matchMedia",
        vi.fn(() => ({ matches })),
    );
}

describe("high contrast preference", () => {
    afterEach(() => {
        localStorage.clear();
        document.documentElement.classList.remove(HIGH_CONTRAST_CLASS);
        vi.unstubAllGlobals();
    });

    it("follows the OS contrast setting when nothing is stored", () => {
        stubPrefersMoreContrast(true);
        expect(isHighContrastPreferred()).toBe(true);

        stubPrefersMoreContrast(false);
        expect(isHighContrastPreferred()).toBe(false);
    });

    it("prefers the stored choice over the OS contrast setting", () => {
        stubPrefersMoreContrast(true);
        setHighContrast(false);

        expect(isHighContrastPreferred()).toBe(false);
    });

    it("toggles the class on the root element", () => {
        setHighContrast(true);
        expect(
            document.documentElement.classList.contains(HIGH_CONTRAST_CLASS),
        ).toBe(true);

        setHighContrast(false);
        expect(
            document.documentElement.classList.contains(HIGH_CONTRAST_CLASS),
        ).toBe(false);
    });
});
