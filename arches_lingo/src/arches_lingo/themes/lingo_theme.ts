import { definePreset, palette } from "@primeuix/themes";
import { ArchesPreset, DEFAULT_THEME } from "@/arches/themes/default.ts";

// const lingoColors = Object.freeze({
//     // Custom Lingo colors that differ from Arches colors in default.ts
// });

const archesPrimitives = ArchesPreset.primitive as {
    arches: {
        legacy: {
            sidebar: string;
        };
        blue: string;
        green: string;
        red: string;
    };
};

export const LingoPreset = definePreset(ArchesPreset, {
    primitive: {
        ...archesPrimitives,
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
            },
        },
    },
    components: {
        button: {
            colorScheme: {
                light: {
                    primary: {
                        background: "{primary-800}",
                        border: {
                            color: "{button-primary-background}",
                        },
                    },
                },
                dark: {
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
