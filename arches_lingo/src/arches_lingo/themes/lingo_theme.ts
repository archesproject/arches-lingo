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
        arches: {
            legacy: {
                sidebarDark: "#b9c9d9", // TODO: use shade from surface palette or pick better color
            },
        },
    },
    semantic: {
        focusRing: {
            width: "0.35rem",
            style: "solid",
            color: "{primary-color}",
            offset: "0.05rem",
            borderRadius: "0.05rem",
        },
        colorScheme: {
            light: {
                primary: palette(archesPrimitives.arches.blue),
                surface: palette("{slate}"),
                sidenav: {
                    background: "{arches.legacy.sidebar}",
                },
                // header: {
                //     background: "{surface.50}",
                // },
                // footer: {
                //     background: "{surface.50}",
                // },
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
                surface: palette("{slate}"),
                sidenav: {
                    background: "{arches.legacy.sidebarDark}",
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
            colorScheme: {
                light: {
                    // @ts-ignore: Ignoring type mismatch for button primary background
                    primary: {
                        background: "{primary-800}",
                        border: {
                            color: "{button-primary-background}",
                        },
                    },
                },
                dark: {
                    // @ts-ignore: Ignoring type mismatch for button primary background
                    primary: {
                        background: "{primary-100}",
                    },
                },
            },
        },
        splitter: {
            colorScheme: {
                light: {
                    // background: "{surface-50}",
                },
                dark: {
                    // @ts-ignore: Ignoring type mismatch for button primary background
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
        // options: {
        //     prefix: "al",
        //     darkModeSelector: ".arches-dark",
        //     cssLayer: false,
        // },
    },
};
