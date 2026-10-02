import type { MergeSection } from "@/arches_lingo/components/concept/ConceptMerge/types.ts";

// Every Concept nodegroup an editor may pull across, in the order the comparison
// view presents them. uri, identifier, part_of_scheme and data_assignment are
// deliberately absent, and the server rejects all four: a shared uri breaks URI
// resolution, identifiers are allocated per scheme, part_of_scheme is identical
// within one scheme, and data_assignment records who asserted the absorbed
// concept's values. This list must stay in step with EXCLUDED_NODEGROUP_ALIASES.
//
// displayNodeAliases decides what a tile card shows; identityNodeAliases decides
// when two tiles count as the same value and must mirror the server's
// IDENTITY_NODES_BY_NODEGROUP. A null identity means the section is never deduped.
//
// schemeScoped marks the sections holding a reference that only resolves inside
// one scheme -- a broader concept, an associated concept, or the scheme itself.
// They are never brought across from a concept in another scheme, and the server
// rejects them too; see SCHEME_SCOPED_NODEGROUP_ALIASES.
//
// isHierarchical marks the sections that place a concept in the hierarchy. They
// are offered but left unselected, so the survivor stays where it is unless the
// editor chooses to move it.
export const MERGE_SECTIONS: MergeSection[] = [
    {
        nodegroupAlias: "appellative_status",
        cardinality: "n",
        displayNodeAliases: [
            "appellative_status_ascribed_name_content",
            "appellative_status_ascribed_name_language",
            "appellative_status_ascribed_relation",
        ],
        identityNodeAliases: [
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
        identityNodeAliases: [
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
        identityNodeAliases: ["classification_status_ascribed_classification"],
        conceptReferenceNodeAliases: [
            "classification_status_ascribed_classification",
        ],
        schemeScoped: true,
        isHierarchical: true,
    },
    {
        nodegroupAlias: "top_concept_of",
        cardinality: "1",
        displayNodeAliases: ["top_concept_of"],
        identityNodeAliases: null,
        schemeScoped: true,
        isHierarchical: true,
    },
    {
        nodegroupAlias: "relation_status",
        cardinality: "n",
        displayNodeAliases: [
            "relation_status_ascribed_comparate",
            "relation_status_ascribed_relation",
        ],
        identityNodeAliases: [
            "relation_status_ascribed_comparate",
            "relation_status_ascribed_relation",
        ],
        conceptReferenceNodeAliases: ["relation_status_ascribed_comparate"],
        schemeScoped: true,
    },
    {
        nodegroupAlias: "match_status",
        cardinality: "n",
        displayNodeAliases: [
            "match_status_ascribed_comparate",
            "match_status_ascribed_relation",
        ],
        identityNodeAliases: [
            "match_status_ascribed_comparate",
            "match_status_ascribed_relation",
        ],
    },
    {
        nodegroupAlias: "type",
        cardinality: "1",
        displayNodeAliases: ["type"],
        identityNodeAliases: null,
    },
    {
        nodegroupAlias: "depicting_digital_asset_internal",
        cardinality: "1",
        displayNodeAliases: ["depicting_digital_asset_internal"],
        identityNodeAliases: null,
        digitalObjectReferenceNodeAliases: ["depicting_digital_asset_internal"],
    },
    {
        nodegroupAlias: "depicting_digital_asset_external",
        cardinality: "1",
        displayNodeAliases: ["depicting_digital_asset_external"],
        identityNodeAliases: null,
    },
    {
        nodegroupAlias: "also_instance_of",
        cardinality: "1",
        displayNodeAliases: ["also_instance_of"],
        identityNodeAliases: null,
    },
    {
        nodegroupAlias: "status",
        cardinality: "1",
        displayNodeAliases: ["status"],
        identityNodeAliases: null,
    },
    {
        nodegroupAlias: "creation",
        cardinality: "1",
        displayNodeAliases: [
            "creation_actor",
            "creation_source_reference",
            "creation_timespan_begin_of_the_begin",
        ],
        identityNodeAliases: null,
    },
];

// Rendered inside the stepper's circular markers, so these are step numbers.
export const MERGE_STEP_SELECT = 1;
export const MERGE_STEP_COMPARE = 2;
export const MERGE_STEP_CONFIRM = 3;

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
