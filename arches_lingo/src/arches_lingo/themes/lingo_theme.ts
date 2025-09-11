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
        lingoFont: {
            family: "'Open Sans',sans-serif",
            size: {
                xxsmall: "0.75rem",
                xsmall: "0.8rem",
                small: "0.875rem",
                smallnormal: "0.95rem",
                normal: "1rem",
                medium: "1.15rem",
                large: "1.25rem",
                xlarge: "1.5rem",
                xxlarge: "2rem",
            },
            weight: {
                light: "300",
                normal: "400",
                medium: "500",
                semibold: "600",
                bold: "700",
                extrabold: "800",
            },
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
                headerToolbar: {
                    background: "{surface.100}",
                    border: "{surface.300}",
                },
                headerButton: {
                    background: "#D1DDE8",
                    border: "#A1B6CB",
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
                sortAndFilterControls: {
                    background: "{light-blue-gray}",
                    border: "{gray}",
                },
                editorForm: {
                    background: "#fcfcfc",
                    color: "#475569",
                },
                schemeCircle: {
                    background: "#4682b4",
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
                    background: "#414A4F",
                    border: "{neutral.500}",
                    itemLabel: "{surface.400}",
                },
                headerToolbar: {
                    background: "{surface.800}",
                    border: "{neutral.600}",
                    itemLabel: "{surface.500}",
                },
                headerButton: {
                    background: "#d7e7f6",
                    border: "#486A8B",
                    color: "#18181b",
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
                sortAndFilterControls: {
                    background: "{surface.700}",
                    border: "{surface.900}",
                },
                editorForm: {
                    background: "#18181B",
                    color: "#f2f2f2",
                },
            },
        },
    },
    components: {
        button: {
            border: {
                radius: "0.125rem",
            },
            colorScheme: {
                light: {
                    // @ts-expect-error: Ignoring type mismatch for button primary background
                    primary: {
                        background: "{button-secondary-background}",
                        borderColor: "{button-primary-background}",
                        color: "{button-secondary-color}",
                        hover: {
                            background: "{primary-700}",
                            borderColor: "{primary-700}",
                        },
                    },
                    danger: {
                        background: "{orange-700}",
                        borderColor: "{orange-700}",
                        hover: {
                            background: "{orange-500}",
                            borderColor: "{orange-500}",
                        },
                    },
                },
                dark: {
                    // @ts-expect-error: Ignoring type mismatch for button primary background
                    primary: {
                        background: "{primary-100}",
                        borderColor: "{button-primary-background}",
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
        menubar: {
            root: {
                color: "{surface-0}",
                background: "{primary-900}",
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
