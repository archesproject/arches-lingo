import { definePreset, palette } from "@primeuix/themes";
import { ArchesPreset, DEFAULT_THEME } from "@/arches/themes/default.ts";
import type { archesPreset } from "@/arches_lingo/types.ts";

const lingoColors = Object.freeze({
    lightBlueGray: "#ebeef0",
    lightGray: "#ebeef0",
    gray: "#dddddd",
});

const archesPrimitives = ArchesPreset.primitive as archesPreset;

export const LingoPreset = definePreset(ArchesPreset, {
    primitive: {
        ...archesPrimitives,
        ...lingoColors,
    },
    semantic: {
        colorScheme: {
            light: {
                primary: palette(archesPrimitives.arches.blue),
                surface: palette("{slate}"),
                sidenav: {
                    background: "{arches.legacy.sidebar}",
                },
                sortAndFilterControls: {
                    background: "{light-blue-gray}",
                    border: "{gray}",
                },
                checkbox: {
                    background: "{light-gray}",
                },
            },
            dark: {
                // DRW: develop Arches blue color for dark mode
                primary: palette(archesPrimitives.arches.blue),
                surface: palette("{zinc}"),
                sidenav: {
                    background: "{surface.800}",
                },
                header: {
                    background: "{surface.900}",
                },
                footer: {
                    background: "{surface.900}",
                },
                sortAndFilterControls: {
                    background: "{surface.700}",
                    border: "{#surface.900}",
                },
                checkbox: {
                    background: "{surface.500}",
                },
            },
        },
    },
    components: {
        button: {
            border: {
                radius: "0.25rem",
            },
            colorScheme: {
                light: {
                    // @ts-expect-error: Ignoring type mismatch for button primary background
                    primary: {
                        background: "{primary-800}",
                        border: {
                            color: "{button-primary-background}",
                        },
                    },
                },
                dark: {
                    // @ts-expect-error: Ignoring type mismatch for button primary background
                    primary: {
                        background: "{primary-100}",
                        border: {
                            color: "{button-primary-background}",
                        },
                    },
                },
            },
        },
        inputtext: {
            // @ts-expect-error: primevue does have border on inputtext
            border: {
                radius: "0.25rem",
            },
        },
        splitter: {
            colorScheme: {
                dark: {
                    // @ts-expect-error: Ignoring type mismatch for button primary background
                    background: "{surface-900}",
                },
            },
        },
    },
});

export const LingoTheme = {
    theme: {
        ...DEFAULT_THEME.theme,
        preset: LingoPreset,
    },
};
