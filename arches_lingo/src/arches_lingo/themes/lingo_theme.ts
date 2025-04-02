import { definePreset, palette } from "@primevue/themes";
import {
    archesColors,
    ArchesPreset,
    DEFAULT_THEME,
} from "@/arches/themes/default.ts";

const lingoColors = Object.freeze({
    // Custom Lingo colors that differ from Arches colors in default.ts
    blue: "#579ddb",
});

export const LingoPreset = definePreset(ArchesPreset, {
    // primitive: {
    //     // arches: {
    //     //     ...lingoColors,
    //     // },
    //     // blue: palette(lingoColors.blue),
    // },
    semantic: {
        colorScheme: {
            light: {
                primary: palette(archesColors.blue),
            },
            dark: {
                // DRW: develop Arches blue color for dark mode
                primary: palette(archesColors.green),
            },
        },
    },
    components: {},
});

export const LingoTheme = {
    theme: {
        ...DEFAULT_THEME.theme,
        preset: LingoPreset,
    },
};
