<script setup lang="ts">
import Drawer from "primevue/drawer";

const shouldShowPageHelpPanel = defineModel("shouldShowPageHelpPanel", {
    type: Boolean,
    default: false,
});
</script>

<template>
    <Drawer
        v-model:visible="shouldShowPageHelpPanel"
        position="right"
        style="min-width: 32rem"
        :header="$gettext('Help')"
        :pt="{
            content: {
                style: {
                    padding: '0',
                    display: 'flex',
                    flexDirection: 'column',
                    fontFamily: 'var(--p-lingo-font-family)',
                },
            },
            header: {
                style: {
                    display: 'flex',
                    justifyContent: 'space-between',
                    backgroundColor: 'var(--p-header-toolbar-background)',
                    borderBottom:
                        '0.0625rem solid var(--p-header-toolbar-border)',
                    padding: '0.25rem 0.75rem',
                    fontFamily: 'var(--p-lingo-font-family)',
                },
            },
        }"
    >
        <div class="help-container">
            <!-- Intro -->
            <div class="help-intro">
                <div class="help-intro-icon">
                    <i class="pi pi-book" />
                </div>
                <div>
                    <h2 class="help-intro-title">
                        {{ $gettext("Arches Lingo") }}
                    </h2>
                    <p class="help-intro-desc">
                        {{
                            $gettext(
                                "A web-based tool for creating and managing controlled vocabularies and thesauri.",
                            )
                        }}
                    </p>
                </div>
            </div>

            <!-- Getting Around -->
            <section class="help-section">
                <h3 class="help-section-title">
                    <i class="pi pi-compass" />
                    {{ $gettext("Getting Around") }}
                </h3>
                <ul class="help-list">
                    <li>
                        <i class="pi pi-home help-list-icon" />
                        <div>
                            <span class="help-term">{{
                                $gettext("Dashboard")
                            }}</span>
                            {{
                                $gettext(
                                    " — your home screen with vocabulary statistics, recent activity, and translation gaps.",
                                )
                            }}
                        </div>
                    </li>
                    <li>
                        <i class="pi pi-lightbulb help-list-icon" />
                        <div>
                            <span class="help-term">{{
                                $gettext("Schemes & Concepts")
                            }}</span>
                            {{
                                $gettext(
                                    " — browse, create, and manage your vocabulary schemes and their concepts.",
                                )
                            }}
                        </div>
                    </li>
                    <li>
                        <i class="pi pi-sitemap help-list-icon" />
                        <div>
                            <span class="help-term">{{
                                $gettext("Explore panel")
                            }}</span>
                            {{
                                $gettext(
                                    " — click Explore in the top bar to open a collapsible hierarchy tree on the left side of the screen.",
                                )
                            }}
                        </div>
                    </li>
                    <li>
                        <i class="pi pi-search help-list-icon" />
                        <div>
                            <span class="help-term">{{
                                $gettext("Search")
                            }}</span>
                            {{
                                $gettext(
                                    " — use the search icon in the header to quickly find any concept or scheme by name.",
                                )
                            }}
                        </div>
                    </li>
                </ul>
            </section>

            <!-- Dashboard -->
            <section class="help-section">
                <h3 class="help-section-title">
                    <i class="pi pi-home" />
                    {{ $gettext("Dashboard") }}
                </h3>
                <p class="help-text">
                    {{
                        $gettext(
                            "The Dashboard gives you a bird's-eye view of your vocabulary data.",
                        )
                    }}
                </p>
                <ul class="help-list">
                    <li>
                        <i class="pi pi-chart-bar help-list-icon" />
                        <div>
                            {{
                                $gettext(
                                    "Stat cards show total Schemes, Concepts, Labels, and the average number of labels per concept.",
                                )
                            }}
                        </div>
                    </li>
                    <li>
                        <i class="pi pi-history help-list-icon" />
                        <div>
                            {{
                                $gettext(
                                    "Recent Activity lists the latest edits across all schemes. Click any resource name to navigate directly to it.",
                                )
                            }}
                        </div>
                    </li>
                    <li>
                        <i class="pi pi-language help-list-icon" />
                        <div>
                            {{
                                $gettext(
                                    "Missing Translations shows concepts that lack a preferred label in a chosen language. Select a language to reveal the list.",
                                )
                            }}
                        </div>
                    </li>
                </ul>
                <div class="help-tip">
                    <i class="pi pi-info-circle help-tip-icon" />
                    {{
                        $gettext(
                            "Use the Schemes filter at the top of the Dashboard to focus all stats and activity on one or more specific schemes.",
                        )
                    }}
                </div>
            </section>

            <!-- Schemes -->
            <section class="help-section">
                <h3 class="help-section-title">
                    <i class="pi pi-folder" />
                    {{ $gettext("Schemes") }}
                </h3>
                <p class="help-text">
                    {{
                        $gettext(
                            'A Scheme is the top-level container for a controlled vocabulary — think of it as the "book" that holds all your concepts.',
                        )
                    }}
                </p>
                <ul class="help-list">
                    <li>
                        <i class="pi pi-plus help-list-icon" />
                        <div>
                            {{
                                $gettext(
                                    "Create a new scheme from the Schemes list, or import one from a SKOS/RDF file.",
                                )
                            }}
                        </div>
                    </li>
                    <li>
                        <i class="pi pi-tag help-list-icon" />
                        <div>
                            <span class="help-term">{{
                                $gettext("Labels")
                            }}</span>
                            {{
                                $gettext(
                                    " — give your scheme a name in one or more languages.",
                                )
                            }}
                        </div>
                    </li>
                    <li>
                        <i class="pi pi-align-left help-list-icon" />
                        <div>
                            <span class="help-term">{{
                                $gettext("Notes")
                            }}</span>
                            {{
                                $gettext(
                                    " — add a scope note, definition, or editorial note to describe the vocabulary's purpose.",
                                )
                            }}
                        </div>
                    </li>
                    <li>
                        <i class="pi pi-link help-list-icon" />
                        <div>
                            <span class="help-term">{{
                                $gettext("Namespace")
                            }}</span>
                            {{
                                $gettext(
                                    " — define a base URI used to mint stable, linked-data identifiers for concepts in this scheme.",
                                )
                            }}
                        </div>
                    </li>
                    <li>
                        <i class="pi pi-verified help-list-icon" />
                        <div>
                            <span class="help-term">{{
                                $gettext("Standards & Rights")
                            }}</span>
                            {{
                                $gettext(
                                    " — record the standards your vocabulary conforms to and the license under which it is published.",
                                )
                            }}
                        </div>
                    </li>
                </ul>
            </section>

            <!-- Concepts -->
            <section class="help-section">
                <h3 class="help-section-title">
                    <i class="pi pi-lightbulb" />
                    {{ $gettext("Concepts") }}
                </h3>
                <p class="help-text">
                    {{
                        $gettext(
                            "A Concept represents a single idea or term in your vocabulary. Concepts live inside Schemes and can be arranged in a hierarchy.",
                        )
                    }}
                </p>
                <ul class="help-list">
                    <li>
                        <i class="pi pi-sitemap help-list-icon" />
                        <div>
                            {{
                                $gettext(
                                    "Lingo supports polyhierarchy — a concept can have multiple broader (parent) concepts and appear in more than one branch of the tree.",
                                )
                            }}
                        </div>
                    </li>
                    <li>
                        <i class="pi pi-images help-list-icon" />
                        <div>
                            <span class="help-term">{{
                                $gettext("Images")
                            }}</span>
                            {{
                                $gettext(
                                    " — attach illustrative images to help identify or describe the concept.",
                                )
                            }}
                        </div>
                    </li>
                    <li>
                        <i class="pi pi-arrows-h help-list-icon" />
                        <div>
                            <span class="help-term">{{
                                $gettext("Related Concepts")
                            }}</span>
                            {{
                                $gettext(
                                    " — link concepts that are semantically associated but do not have a broader/narrower relationship.",
                                )
                            }}
                        </div>
                    </li>
                    <li>
                        <i class="pi pi-external-link help-list-icon" />
                        <div>
                            <span class="help-term">{{
                                $gettext("Matched Concepts")
                            }}</span>
                            {{
                                $gettext(
                                    " — map this concept to equivalent terms in external thesauri or authority files (e.g. exactMatch, closeMatch).",
                                )
                            }}
                        </div>
                    </li>
                </ul>
                <div class="help-tip">
                    <i class="pi pi-info-circle help-tip-icon" />
                    {{
                        $gettext(
                            'To add a child concept, open the Explore panel and use the "+" icon that appears when hovering over a concept in the tree.',
                        )
                    }}
                </div>
            </section>

            <!-- Labels -->
            <section class="help-section">
                <h3 class="help-section-title">
                    <i class="pi pi-tag" />
                    {{ $gettext("Labels") }}
                </h3>
                <p class="help-text">
                    {{
                        $gettext(
                            "Every concept should have at least one Preferred Label. Labels can be added in multiple languages.",
                        )
                    }}
                </p>
                <div class="help-label-types">
                    <div class="help-label-type">
                        <span class="help-badge help-badge--preferred">{{
                            $gettext("Preferred")
                        }}</span>
                        <span class="help-label-desc">{{
                            $gettext(
                                "The primary display term. Each concept should have exactly one per language.",
                            )
                        }}</span>
                    </div>
                    <div class="help-label-type">
                        <span class="help-badge help-badge--alternate">{{
                            $gettext("Alternate")
                        }}</span>
                        <span class="help-label-desc">{{
                            $gettext(
                                "Synonyms or variant spellings — help users find the concept via different terms.",
                            )
                        }}</span>
                    </div>
                    <div class="help-label-type">
                        <span class="help-badge help-badge--hidden">{{
                            $gettext("Hidden")
                        }}</span>
                        <span class="help-label-desc">{{
                            $gettext(
                                "Used for search indexing only — not shown in displays or exports.",
                            )
                        }}</span>
                    </div>
                </div>
                <div class="help-tip">
                    <i class="pi pi-info-circle help-tip-icon" />
                    {{
                        $gettext(
                            "Use the Missing Translations table on the Dashboard to identify concepts that still need a preferred label in a given language.",
                        )
                    }}
                </div>
            </section>

            <!-- Import & Export -->
            <section class="help-section">
                <h3 class="help-section-title">
                    <i class="pi pi-arrow-right-arrow-left" />
                    {{ $gettext("Import & Export") }}
                </h3>
                <ul class="help-list">
                    <li>
                        <i class="pi pi-upload help-list-icon" />
                        <div>
                            {{
                                $gettext(
                                    "Import an existing thesaurus in SKOS/RDF format from the Schemes list page using the Import button. Hierarchies, labels, and notes are preserved.",
                                )
                            }}
                        </div>
                    </li>
                    <li>
                        <i class="pi pi-download help-list-icon" />
                        <div>
                            {{
                                $gettext(
                                    "Export any scheme from its detail page to share your vocabulary or use it in another system.",
                                )
                            }}
                        </div>
                    </li>
                </ul>
            </section>

            <!-- Support -->
            <section class="help-section help-section--last">
                <h3 class="help-section-title">
                    <i class="pi pi-question-circle" />
                    {{ $gettext("Support & Resources") }}
                </h3>
                <ul class="help-list">
                    <li>
                        <i class="pi pi-github help-list-icon" />
                        <div>
                            {{ $gettext("Report issues or contribute on ") }}
                            <a
                                class="help-link"
                                href="https://github.com/archesproject/arches-lingo"
                                target="_blank"
                                rel="noopener noreferrer"
                                >GitHub</a
                            >
                        </div>
                    </li>
                    <li>
                        <i class="pi pi-book help-list-icon" />
                        <div>
                            {{ $gettext("Visit ") }}
                            <a
                                class="help-link"
                                href="https://www.archesproject.org"
                                target="_blank"
                                rel="noopener noreferrer"
                                >archesproject.org</a
                            >
                            {{ $gettext(" for platform documentation.") }}
                        </div>
                    </li>
                </ul>
            </section>
        </div>
    </Drawer>
</template>

<style scoped>
.help-container {
    overflow-y: auto;
    display: flex;
    flex-direction: column;
    height: 100%;
    font-size: var(--p-lingo-font-size-smallnormal);
    color: var(--p-text-color);
}

/* ── Intro ── */
.help-intro {
    display: flex;
    align-items: flex-start;
    gap: 0.75rem;
    padding: 1.25rem 1rem;
    background: var(--p-highlight-background);
    border-bottom: 0.0625rem solid var(--p-header-toolbar-border);
}

.help-intro-icon {
    display: flex;
    align-items: center;
    justify-content: center;
    width: 2.5rem;
    height: 2.5rem;
    min-width: 2.5rem;
    border-radius: 50%;
    background: var(--p-primary-100);
    color: var(--p-primary-600);
    font-size: 1.125rem;
}

.help-intro-title {
    margin: 0 0 0.25rem;
    font-size: var(--p-lingo-font-size-medium);
    font-weight: var(--p-lingo-font-weight-normal);
    color: var(--p-text-color);
}

.help-intro-desc {
    margin: 0;
    font-size: var(--p-lingo-font-size-small);
    color: var(--p-neutral-500);
    line-height: 1.5;
}

/* ── Sections ── */
.help-section {
    padding: 1rem;
    border-bottom: 0.0625rem solid var(--p-header-toolbar-border);
}

.help-section--last {
    border-bottom: none;
}

.help-section-title {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    margin: 0 0 0.75rem;
    font-size: var(--p-lingo-font-size-xsmall);
    font-weight: var(--p-lingo-font-weight-normal);
    color: var(--p-neutral-500);
    text-transform: uppercase;
    letter-spacing: 0.06em;
}

.help-section-title .pi {
    font-size: 0.8125rem;
    color: var(--p-primary-500);
}

.help-text {
    margin: 0 0 0.75rem;
    font-size: var(--p-lingo-font-size-small);
    color: var(--p-neutral-500);
    line-height: 1.5;
}

/* ── List ── */
.help-list {
    list-style: none;
    margin: 0;
    padding: 0;
    display: flex;
    flex-direction: column;
    gap: 0.625rem;
}

.help-list li {
    display: flex;
    align-items: flex-start;
    gap: 0.5rem;
    font-size: var(--p-lingo-font-size-small);
    line-height: 1.5;
    color: var(--p-text-color);
}

.help-list-icon {
    font-size: 0.75rem;
    color: var(--p-primary-400);
    min-width: 0.75rem;
    margin-top: 0.25rem;
}

.help-term {
    font-weight: var(--p-lingo-font-weight-normal);
    color: var(--p-text-color);
}

/* ── Tip box ── */
.help-tip {
    display: flex;
    align-items: flex-start;
    gap: 0.5rem;
    margin-top: 0.875rem;
    padding: 0.625rem 0.75rem;
    background: var(--p-highlight-background);
    border-left: 0.1875rem solid var(--p-primary-400);
    border-radius: 0 0.125rem 0.125rem 0;
    font-size: var(--p-lingo-font-size-small);
    color: var(--p-neutral-600);
    line-height: 1.5;
}

.help-tip-icon {
    font-size: 0.75rem;
    color: var(--p-primary-500);
    min-width: 0.75rem;
    margin-top: 0.2rem;
}

/* ── Label type grid ── */
.help-label-types {
    display: flex;
    flex-direction: column;
    gap: 0.625rem;
}

.help-label-type {
    display: flex;
    align-items: flex-start;
    gap: 0.75rem;
}

.help-badge {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    padding: 0.125rem 0.5rem;
    border-radius: 0.125rem;
    font-size: var(--p-lingo-font-size-xsmall);
    font-weight: var(--p-lingo-font-weight-normal);
    white-space: nowrap;
    min-width: 5.25rem;
}

.help-badge--preferred {
    background: var(--p-primary-100);
    color: var(--p-primary-700);
    border: 0.0625rem solid var(--p-primary-200);
}

.help-badge--alternate {
    background: var(--p-highlight-background);
    color: var(--p-neutral-600);
    border: 0.0625rem solid var(--p-highlight-focus-background);
}

.help-badge--hidden {
    background: var(--p-content-background);
    color: var(--p-neutral-500);
    border: 0.0625rem solid var(--p-header-toolbar-border);
}

.help-label-desc {
    font-size: var(--p-lingo-font-size-small);
    color: var(--p-neutral-500);
    line-height: 1.5;
}

/* ── Link ── */
.help-link {
    color: var(--p-primary-500);
    text-decoration: none;
}

.help-link:hover {
    text-decoration: underline;
}
</style>
