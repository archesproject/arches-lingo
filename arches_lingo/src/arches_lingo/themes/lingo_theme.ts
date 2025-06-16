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
        lingoEditor: {
            headerFontSize: "1.15rem",
            headerFontWeight: "400",
        },
        colorScheme: {
            light: {
                primary: palette(archesPrimitives.arches.blue),
                surface: palette("{slate}"),
                checkbox: {
                    background: "{light-gray}",
                },
                header: {
                    background: "{surface.50}",
                    border: "{neutral.300}",
                    itemLabel: "{surface.500}",
                },
                searchResult: {
                    color: "{sky.600}",
                    borderBottom: "{zinc.200}",
                    isEven: {
                        background: "{surface.100}",
                    },
                    focus: {
                        background: "{sky.100}",
                    },
                },
                searchResultHierarchy: {
                    color: "{zinc.400}",
                },
                sidenav: {
                    backgroundColor: "{arches.legacy.sidebar}",
                },
                sortAndFilterControls: {
                    background: "{light-blue-gray}",
                    border: "{gray}",
                },
            },
            dark: {
                primary: palette(archesPrimitives.arches.blue),
                surface: palette("{zinc}"),
                checkbox: {
                    background: "{surface.500}",
                },
                footer: {
                    background: "{surface.900}",
                },
                header: {
                    background: "{surface.700}",
                    border: "{neutral.500}",
                    itemLabel: "{surface.400}",
                },
                searchResult: {
                    borderBottom: "{surface.900}",
                    isEven: {
                        background: "{surface.800}",
                    },
                    focus: {
                        background: "{sky.900}",
                    },
                },
                searchResultHierarchy: {
                    color: "{zinc.400}",
                },
                sidenav: {
                    background: "{surface.800}",
                },
                sortAndFilterControls: {
                    background: "{surface.700}",
                    border: "{surface.900}",
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
                    danger: {
                        background: "{button-warn-active-background}",
                        borderColor: "{button-warn-active-background}",
                        hover: {
                            background: "{button-warn-background}",
                            borderColor: "{button-warn-background}",
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
