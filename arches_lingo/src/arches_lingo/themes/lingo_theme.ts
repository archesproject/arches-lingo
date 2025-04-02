import { definePreset, palette } from "@primevue/themes";
import { ArchesPreset, DEFAULT_THEME } from "@/arches/themes/default.ts";

const lingoColors = Object.freeze({
    // Custom Lingo colors that differ from Arches colors in default.ts
});

export const LingoPreset = definePreset(ArchesPreset, {
    primitive: {
        arches: {
            ...lingoColors,
        },
        // blue: palette(lingoColors.blue),
    },
    semantic: {},
    components: {},
});

export const LingoTheme = {
    theme: {
        ...DEFAULT_THEME.theme,
        preset: LingoPreset,
    },
};
