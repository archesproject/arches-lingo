import type { MergeSection } from "@/arches_lingo/components/concept/ConceptMerge/types.ts";

// The Concept sections the comparison step shows, in order. The server decides
// which tiles in them can be taken (see MERGE_SECTION_RULES), so these only say
// how each section is displayed. isHierarchical sections are offered but left
// unselected, so the survivor stays where it is unless the editor moves it.
export const MERGE_SECTIONS: MergeSection[] = [
    {
        nodegroupAlias: "appellative_status",
        cardinality: "n",
        displayNodeAliases: [
            "appellative_status_ascribed_name_content",
            "appellative_status_ascribed_name_language",
            "appellative_status_ascribed_relation",
        ],
    },
    {
        nodegroupAlias: "statement",
        cardinality: "n",
        displayNodeAliases: [
            "statement_content",
            "statement_language",
            "statement_type",
        ],
    },
    {
        nodegroupAlias: "classification_status",
        cardinality: "n",
        displayNodeAliases: [
            "classification_status_ascribed_classification",
            "classification_status_type",
        ],
        conceptReferenceNodeAliases: [
            "classification_status_ascribed_classification",
        ],
        isHierarchical: true,
    },
    {
        nodegroupAlias: "top_concept_of",
        cardinality: "1",
        displayNodeAliases: ["top_concept_of"],
        isHierarchical: true,
    },
    {
        nodegroupAlias: "relation_status",
        cardinality: "n",
        displayNodeAliases: [
            "relation_status_ascribed_comparate",
            "relation_status_ascribed_relation",
        ],
        conceptReferenceNodeAliases: ["relation_status_ascribed_comparate"],
    },
    {
        nodegroupAlias: "match_status",
        cardinality: "n",
        displayNodeAliases: [
            "match_status_ascribed_comparate",
            "match_status_ascribed_relation",
        ],
    },
    {
        nodegroupAlias: "type",
        cardinality: "1",
        displayNodeAliases: ["type"],
    },
    {
        nodegroupAlias: "depicting_digital_asset_internal",
        cardinality: "1",
        displayNodeAliases: ["depicting_digital_asset_internal"],
        digitalObjectReferenceNodeAliases: ["depicting_digital_asset_internal"],
    },
    {
        nodegroupAlias: "depicting_digital_asset_external",
        cardinality: "1",
        displayNodeAliases: ["depicting_digital_asset_external"],
    },
    {
        nodegroupAlias: "also_instance_of",
        cardinality: "1",
        displayNodeAliases: ["also_instance_of"],
    },
    {
        nodegroupAlias: "status",
        cardinality: "1",
        displayNodeAliases: ["status"],
    },
    {
        nodegroupAlias: "creation",
        cardinality: "1",
        displayNodeAliases: [
            "creation_actor",
            "creation_source_reference",
            "creation_timespan_begin_of_the_begin",
        ],
    },
];

// Rendered inside the stepper's circular markers, so these are step numbers.
export const MERGE_STEP_SELECT = 1;
export const MERGE_STEP_COMPARE = 2;
export const MERGE_STEP_CONFIRM = 3;

export const TILE_STATE_ALREADY_ON_SURVIVOR = "already_on_survivor";
export const TILE_STATE_DROPPED = "dropped";

// The frame every merge dialog shares; each adds its own size and content.
export const MERGE_DIALOG_FRAME_PASS_THROUGH = {
    root: {
        style: {
            fontFamily: "var(--p-lingo-font-family)",
            fontSize: "var(--p-lingo-font-size-small)",
            border: "0.125rem solid var(--p-dialog-color)",
            borderRadius: "0.25rem",
        },
    },
    header: {
        style: {
            background: "var(--p-navigation-header-color)",
            color: "var(--p-dialog-header-text-color)",
            borderRadius: "0",
            paddingBlock: "1.25rem",
            paddingInline: "1.5rem",
        },
    },
    title: {
        style: {
            fontSize: "var(--p-lingo-font-size-large)",
            fontWeight: "var(--p-lingo-font-weight-normal)",
            lineHeight: "1.2",
        },
    },
};
