import { definePreset, palette } from "@primeuix/themes";
import { ArchesPreset, DEFAULT_THEME } from "@/arches/themes/default.ts";
import type { archesPreset } from "@/arches_lingo/types.ts";

const lingoColors = Object.freeze({
    offWhite: "#fcfcfc",
    lightBlueGray: "#ebeef0",
    lightGray: "#ebeef0",
    gray: "#dddddd",
    lightNeutralGray: "#f2f2f2",
    paleBlue: "#d7e7f6",
    softBlueGray: "#D1DDE8",
    mutedBlueGray: "#A1B6CB",
    steelBlue: "#4682b4",
    deepSteelBlue: "#486A8B",
    slateGray: "#475569",
    charcoalGray: "#414A4F",
    nearBlack: "#18181B",
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
        lingoAccent: {
            color: "{primary.500}",
            strongColor: "{primary.600}",
            strongerColor: "{primary.700}",
            hoverBackground: "{primary.50}",
            softColor: "{primary.400}",
        },
        lingoAccentBadge: {
            color: "{primary.700}",
            softColor: "{primary.600}",
        },
        lingoMuted: {
            color: "{neutral.400}",
            strongColor: "{neutral.500}",
            strongerColor: "{neutral.600}",
        },
        lingoSelectionIndicator: {
            color: "{primary.400}",
        },
        lingoFormSubtitle: {
            color: "{form.field.hover.border.color}",
        },
        lingoLanguageChip: {
            background: "{navigation.item.icon.color}",
        },
        lingoNavigationBar: {
            background: "{primary.900}",
            color: "{surface.0}",
            hoverBackground: "{primary.hover.color}",
        },
        lingoDivider: {
            color: "{highlight.focus.background}",
        },
        lingoQueryBuilder: {
            groupOutlineColor: "transparent",
            ruleColor: "transparent",
        },
        lingoDimmed: {
            alreadyPresentOpacity: "0.6",
            unavailableOpacity: "0.65",
        },
        colorScheme: {
            light: {
                primary: palette(archesPrimitives.arches.blue),
                surface: palette("{slate}"),
                checkbox: {
                    background: "{light-gray}",
                },
                dialog: {
                    headerTextColor: "{slate.50}",
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
                    background: "{soft-blue-gray}",
                    border: "{muted-blue-gray}",
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
                helpPanel: {
                    intro: {
                        color: "{lingo.muted.strong.color}",
                    },
                    sectionTitle: {
                        color: "{lingo.muted.stronger.color}",
                    },
                },
                sortAndFilterControls: {
                    background: "{light-blue-gray}",
                    border: "{gray}",
                },
                editorForm: {
                    background: "{off-white}",
                    color: "{slate-gray}",
                },
                schemeCircle: {
                    background: "{steel-blue}",
                },
            },
            dark: {
                primary: palette(archesPrimitives.arches.blue),
                surface: palette("{zinc}"),
                checkbox: {
                    background: "{surface.500}",
                },
                dialog: {
                    headerTextColor: "{slate.50}",
                },
                footer: {
                    background: "{surface.900}",
                },
                header: {
                    background: "{charcoal-gray}",
                    border: "{neutral.500}",
                    itemLabel: "{surface.400}",
                },
                headerToolbar: {
                    background: "{surface.800}",
                    border: "{neutral.600}",
                },
                headerButton: {
                    background: "{pale-blue}",
                    border: "{deep-steel-blue}",
                    color: "{near-black}",
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
                    background: "{near-black}",
                    color: "{light-neutral-gray}",
                },
            },
        },
    },
    components: {
        button: {
            root: {
                borderRadius: "0.125rem",
            },
        },
        dialog: {
            title: {
                fontSize: "{lingo-font-size-normal}",
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
                color: "{lingo-navigation-bar-color}",
                background: "{lingo-navigation-bar-background}",
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
