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
                    <li>
                        <i class="pi pi-user-edit help-list-icon" />
                        <div>
                            <span class="help-term">{{
                                $gettext("Reference Data")
                            }}</span>
                            {{
                                $gettext(
                                    " — find Contributors and Sources in this sidebar section to manage the people, organizations, and bibliographic references that support your vocabulary.",
                                )
                            }}
                        </div>
                    </li>
                    <li>
                        <i class="pi pi-user help-list-icon" />
                        <div>
                            <span class="help-term">{{
                                $gettext("Settings")
                            }}</span>
                            {{
                                $gettext(
                                    " — access your Profile from the Settings section of the sidebar to update your name, email, and password.",
                                )
                            }}
                        </div>
                    </li>
                </ul>
                <div class="help-tip">
                    <i class="pi pi-info-circle help-tip-icon" />
                    {{
                        $gettext(
                            "Lingo will warn you before navigating away if you have unsaved edits on the current page.",
                        )
                    }}
                </div>
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
                        <i class="pi pi-hashtag help-list-icon" />
                        <div>
                            <span class="help-term">{{
                                $gettext("Identifier")
                            }}</span>
                            {{
                                $gettext(
                                    " — a short code for the scheme (e.g. ",
                                )
                            }}<em>{{ $gettext("GETT") }}</em
                            >{{ $gettext("). Used as the ")
                            }}<code class="help-code"
                                >&lt;scheme_identifier&gt;</code
                            >{{ $gettext(" placeholder in the URI template.") }}
                        </div>
                    </li>
                    <li>
                        <i class="pi pi-link help-list-icon" />
                        <div>
                            <span class="help-term">{{
                                $gettext("URI template")
                            }}</span>
                            {{
                                $gettext(
                                    " — the pattern used to mint stable linked-data URIs for every concept when the scheme is published. Use the placeholders ",
                                )
                            }}<code class="help-code"
                                >&lt;scheme_identifier&gt;</code
                            >
                            {{ $gettext("and ") }}
                            <code class="help-code"
                                >&lt;concept_identifier&gt;</code
                            >
                            {{ $gettext(" to build the URI structure.") }}
                        </div>
                    </li>
                    <li>
                        <i class="pi pi-sort-numeric-up help-list-icon" />
                        <div>
                            <span class="help-term">{{
                                $gettext("Concept counter")
                            }}</span>
                            {{
                                $gettext(
                                    " — the starting number for auto-incrementing concept identifiers. Set this before publishing — once identifiers have been assigned the counter is locked.",
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

            <!-- Advanced Search -->
            <section class="help-section">
                <h3 class="help-section-title">
                    <i class="pi pi-search" />
                    {{ $gettext("Advanced Search") }}
                </h3>
                <p class="help-text">
                    {{
                        $gettext(
                            "Build complex queries to find concepts across all schemes using multiple criteria at once.",
                        )
                    }}
                </p>
                <ul class="help-list">
                    <li>
                        <i class="pi pi-filter help-list-icon" />
                        <div>
                            <span class="help-term">{{
                                $gettext("Query builder")
                            }}</span>
                            {{
                                $gettext(
                                    " — combine facets such as label, scheme, language, note content, URI, identifier, and lifecycle state. Group conditions with AND / OR logic.",
                                )
                            }}
                        </div>
                    </li>
                    <li>
                        <i class="pi pi-save help-list-icon" />
                        <div>
                            <span class="help-term">{{
                                $gettext("Saved searches")
                            }}</span>
                            {{
                                $gettext(
                                    " — save your current query for quick re-use later. Saved searches appear in the Collections panel on the right.",
                                )
                            }}
                        </div>
                    </li>
                    <li>
                        <i class="pi pi-folder help-list-icon" />
                        <div>
                            <span class="help-term">{{
                                $gettext("Concept sets")
                            }}</span>
                            {{
                                $gettext(
                                    " — group selected concepts into named sets. Add concepts from search results, view a set's members, or remove concepts from a set.",
                                )
                            }}
                        </div>
                    </li>
                    <li>
                        <i class="pi pi-check-square help-list-icon" />
                        <div>
                            {{
                                $gettext(
                                    "Use the checkboxes in search results to select concepts, then use the Concept Sets actions to add or remove them.",
                                )
                            }}
                        </div>
                    </li>
                    <li>
                        <i class="pi pi-objects-column help-list-icon" />
                        <div>
                            {{
                                $gettext(
                                    "Click the Collections button in the toolbar to show or hide the Saved Searches and Concept Sets panel.",
                                )
                            }}
                        </div>
                    </li>
                </ul>
                <div class="help-tip">
                    <i class="pi pi-info-circle help-tip-icon" />
                    {{
                        $gettext(
                            "Expand a search result row to see additional details such as identifier, lifecycle state, and notes.",
                        )
                    }}
                </div>
            </section>

            <!-- Lifecycle States -->
            <section class="help-section">
                <h3 class="help-section-title">
                    <i class="pi pi-refresh" />
                    {{ $gettext("Lifecycle States") }}
                </h3>
                <p class="help-text">
                    {{
                        $gettext(
                            "Every scheme and concept has a lifecycle state that tracks its maturity from initial creation through to publication and eventual retirement.",
                        )
                    }}
                </p>
                <div class="help-label-types">
                    <div class="help-label-type">
                        <span class="help-badge help-badge--lifecycle-draft">{{
                            $gettext("Draft")
                        }}</span>
                        <span class="help-label-desc">{{
                            $gettext(
                                "Initial working state. The record can be freely edited and deleted.",
                            )
                        }}</span>
                    </div>
                    <div class="help-label-type">
                        <span
                            class="help-badge help-badge--lifecycle-editing"
                            >{{ $gettext("Editing") }}</span
                        >
                        <span class="help-label-desc">{{
                            $gettext(
                                "Back under active revision after prior publication.",
                            )
                        }}</span>
                    </div>
                    <div class="help-label-type">
                        <span
                            class="help-badge help-badge--lifecycle-published"
                            >{{ $gettext("Published") }}</span
                        >
                        <span class="help-label-desc">{{
                            $gettext(
                                "Finalized and stable. The URI is now authoritative.",
                            )
                        }}</span>
                    </div>
                    <div class="help-label-type">
                        <span
                            class="help-badge help-badge--lifecycle-retired"
                            >{{ $gettext("Retired") }}</span
                        >
                        <span class="help-label-desc">{{
                            $gettext(
                                "No longer active. Retired records are preserved for reference and their URIs remain resolvable.",
                            )
                        }}</span>
                    </div>
                </div>
                <ul
                    class="help-list"
                    style="margin-top: 0.875rem"
                >
                    <li>
                        <i class="pi pi-tag help-list-icon" />
                        <div>
                            <span class="help-term">{{
                                $gettext("State badges")
                            }}</span>
                            {{
                                $gettext(
                                    " — the current state appears as a color-coded badge in concept and scheme headers and in search results. In the hierarchy tree, badges are shown for Draft and Retired records so they stand out at a glance.",
                                )
                            }}
                        </div>
                    </li>
                    <li>
                        <i
                            class="pi pi-arrow-right-arrow-left help-list-icon"
                        />
                        <div>
                            <span class="help-term">{{
                                $gettext("Scheme-level transitions")
                            }}</span>
                            {{
                                $gettext(
                                    " — Publishing and moving a scheme back into Editing are controlled from the scheme header and cascade automatically to all of its concepts. When a scheme is published, concept identifiers and URIs are generated for every concept using the scheme's identifier, URI template, and concept counter.",
                                )
                            }}
                        </div>
                    </li>
                    <li>
                        <i class="pi pi-trash help-list-icon" />
                        <div>
                            <span class="help-term">{{
                                $gettext("Concept-level actions")
                            }}</span>
                            {{
                                $gettext(
                                    " — at the concept level, editors can delete a Draft concept (permanent removal) or deprecate an Editing concept (soft retirement that preserves its URI and history). Publish and Editing transitions are not available directly on individual concepts.",
                                )
                            }}
                        </div>
                    </li>
                    <li>
                        <i class="pi pi-filter help-list-icon" />
                        <div>
                            <span class="help-term">{{
                                $gettext("Lifecycle filter")
                            }}</span>
                            {{
                                $gettext(
                                    " — use the filter button in the Explore panel to show only concepts in one or more specific states, for example to review all Draft concepts before publishing a scheme.",
                                )
                            }}
                        </div>
                    </li>
                </ul>
                <div class="help-tip">
                    <i class="pi pi-info-circle help-tip-icon" />
                    {{
                        $gettext(
                            "You can also filter by lifecycle state in the Advanced Search query builder to find all concepts at a particular stage across every scheme.",
                        )
                    }}
                </div>
            </section>

            <!-- Reference Data -->
            <section class="help-section">
                <h3 class="help-section-title">
                    <i class="pi pi-database" />
                    {{ $gettext("Reference Data") }}
                </h3>
                <p class="help-text">
                    {{
                        $gettext(
                            "The Reference Data section of the sidebar lets you manage supporting resources that can be linked to vocabulary content.",
                        )
                    }}
                </p>
                <ul class="help-list">
                    <li>
                        <i class="pi pi-user-edit help-list-icon" />
                        <div>
                            <span class="help-term">{{
                                $gettext("Contributors")
                            }}</span>
                            {{
                                $gettext(
                                    " — manage the people and organizations that contribute to your vocabularies. Contributors can be recorded as individuals (Person) or as collective bodies (Group).",
                                )
                            }}
                        </div>
                    </li>
                    <li>
                        <i class="pi pi-bookmark-fill help-list-icon" />
                        <div>
                            <span class="help-term">{{
                                $gettext("Sources")
                            }}</span>
                            {{
                                $gettext(
                                    " — record the bibliographic sources that inform or support your vocabulary content, such as reference publications or authority files.",
                                )
                            }}
                        </div>
                    </li>
                </ul>
            </section>

            <!-- Profile -->
            <section class="help-section">
                <h3 class="help-section-title">
                    <i class="pi pi-user" />
                    {{ $gettext("Your Profile") }}
                </h3>
                <p class="help-text">
                    {{
                        $gettext(
                            "Access your profile from Settings > Profile in the sidebar.",
                        )
                    }}
                </p>
                <ul class="help-list">
                    <li>
                        <i class="pi pi-id-card help-list-icon" />
                        <div>
                            {{
                                $gettext(
                                    "Update your display name, email address, and phone number.",
                                )
                            }}
                        </div>
                    </li>
                    <li>
                        <i class="pi pi-lock help-list-icon" />
                        <div>
                            {{
                                $gettext(
                                    "Change your password using the Password section — enter your current password and choose a new one.",
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
    border-bottom: 0.0625rem solid var(--p-header-toolbar-border);
    padding-bottom: .75rem;
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
    color: var(--p-neutral-600);
    text-transform: uppercase;
    letter-spacing: 0.06em;
    padding: 1rem;
    background: var(--p-datatable-row-striped-background);
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
    padding: 0 1rem;
}

/* ── List ── */
.help-list {
    list-style: none;
    margin: 0;
    padding: 1.0rem;
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
    margin: 0.875rem;
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
    padding: 0 1rem;
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

.help-badge--lifecycle-draft {
    background: var(--p-tag-secondary-background);
    color: var(--p-tag-secondary-color);
    border: 0.0625rem solid var(--p-tag-secondary-border-color);
}

.help-badge--lifecycle-editing {
    background: var(--p-tag-warn-background);
    color: var(--p-tag-warn-color);
    border: 0.0625rem solid var(--p-tag-warn-border-color);
}

.help-badge--lifecycle-published {
    background: var(--p-tag-success-background);
    color: var(--p-tag-success-color);
    border: 0.0625rem solid var(--p-tag-success-border-color);
}

.help-badge--lifecycle-retired {
    background: var(--p-tag-danger-background);
    color: var(--p-tag-danger-color);
    border: 0.0625rem solid var(--p-tag-danger-border-color);
}

.help-label-desc {
    font-size: var(--p-lingo-font-size-small);
    color: var(--p-neutral-500);
    line-height: 1.5;
}

/* ── Inline code ── */
.help-code {
    font-family: monospace;
    font-size: var(--p-lingo-font-size-xsmall);
    background: var(--p-highlight-background);
    border: 0.0625rem solid var(--p-header-toolbar-border);
    border-radius: 0.125rem;
    padding: 0 0.25rem;
    color: var(--p-text-color);
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
