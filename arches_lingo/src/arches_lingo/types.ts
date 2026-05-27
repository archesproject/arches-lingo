import type { Component, Ref } from "vue";
import type { MenuItem } from "primevue/menuitem";
import type { TreeNode } from "primevue/treenode";
import type { EDIT, VIEW } from "@/arches_lingo/constants.ts";

import type { ReferenceSelectTreeNode } from "@/arches_controlled_lists/datatypes/reference-select/types.ts";
import type { Label } from "@/arches_controlled_lists/types.ts";

import type { StringAliasedNodeData } from "@/arches_component_lab/datatypes/string/types.ts";
import type {
    ResourceInstanceListAliasedNodeData,
    ResourceInstanceReference,
} from "@/arches_component_lab/datatypes/resource-instance-list/types.ts";
import type { FileListAliasedNodeData } from "@/arches_component_lab/datatypes/file-list/types.ts";

export interface User {
    first_name: string;
    last_name: string;
    username: string;
    email: string;
    phone?: string;
    is_lingo_editor: boolean;
    is_anonymous: boolean;
    is_staff: boolean;
}

export interface AppSettings {
    allow_anonymous_access: boolean;
    public_server_address: string | null;
    arches_version: string;
    lingo_version: string;
}

export interface DisplayedRowRefAndSetter {
    displayedRow: Ref<Concept | Scheme | null>;
    setDisplayedRow: (val: Concept | Scheme | null) => void;
}

export interface HierarchyRefAndSetter {
    hierarchyVisible: Ref<boolean>;
    toggleHierarchy: () => void;
}

export interface Concept {
    id: string;
    labels: Label[];
    narrower: Concept[];
    has_narrower?: boolean;
    guide_term?: boolean;
    hierarchy_name?: boolean;
    top_concept?: boolean;
    resource_instance_lifecycle_state_id?: string;
    resource_instance_lifecycle_state_name?: string;
}

export type ConceptPathNode = Pick<
    Concept,
    "id" | "labels" | "guide_term" | "hierarchy_name" | "top_concept"
>;

export interface Scheme {
    id: string;
    labels: Label[];
    top_concepts: Concept[];
    resource_instance_lifecycle_state_id?: string;
    resource_instance_lifecycle_state_name?: string;
}

export interface ControlledListResult {
    id: string;
    name: string;
    items: ReferenceSelectTreeNode[];
}

export interface ControlledListItemLabelValue {
    id: string;
    valuetype_id: string;
    language_id: string;
    value: string;
    list_item_id: string;
}

export interface ControlledListItemResult {
    id?: string;
    list_id: string;
    uri: string;
    sortorder?: number;
    guide?: boolean;
    values: ControlledListItemLabelValue[];
    children: ControlledListItemResult[];
    depth: number;
}

export interface ResourceInstanceResult {
    resourceinstanceid: string;
    name?: string | undefined;
    descriptors: {
        [key: string]: {
            name: string;
            description: string;
        };
    };
    aliased_data?: {
        // TODO: Make this exstensible for various types of aliased_data
        // eslint-disable-next-line
        [key: string]: any;
    };
    principalUser?: number | string;
    principal_user_display_name?: string | null;
    resource_instance_lifecycle_state?: string;
}

export interface ResourceSummary {
    resourceinstanceid: string;
    display_name: string;
    graph_slug: string;
    graph_name: string;
}

export interface PaginatedResourceListResponse {
    count: number;
    results: ResourceSummary[];
}

export type DataComponentMode = typeof EDIT | typeof VIEW;

export interface MetaStringText {
    name: string;
    type: string;
    language?: string;
    deleteConfirm: string;
    noRecords: string;
    sortFields?: {
        name?: string;
        type?: string;
        language?: string;
    };
}

// eslint-disable-next-line
interface AliasedData {}

export interface TileData<T extends AliasedData = AliasedData> {
    resourceinstance?: string;
    tileid?: string;
    aliased_data: T;
}

export interface ResourceData<T extends AliasedData = AliasedData> {
    display_value?: string;
    resourceinstanceid: string;
    aliased_data: T;
}

interface QuerysetsReferenceSelectFetchedOption {
    display_value: string;
    node_value: ReferenceSelectTreeNode[];
    details: unknown[];
}

export interface AppellativeStatusAliases extends AliasedData {
    appellative_status_ascribed_name_content: StringAliasedNodeData;
    appellative_status_ascribed_name_language?: QuerysetsReferenceSelectFetchedOption;
    appellative_status_ascribed_relation?: QuerysetsReferenceSelectFetchedOption;
    appellative_status_status_metatype?: QuerysetsReferenceSelectFetchedOption;
    appellative_status_status?: QuerysetsReferenceSelectFetchedOption;
    appellative_status_data_assignment_object_used: ResourceInstanceListAliasedNodeData;
    appellative_status_data_assignment_actor: ResourceInstanceListAliasedNodeData;
    appellative_status_data_assignment_type: QuerysetsReferenceSelectFetchedOption;
    appellative_status_timespan_begin_of_the_begin: StringAliasedNodeData;
    appellative_status_timespan_end_of_the_end: StringAliasedNodeData;
}

export interface ConceptNameAlises extends AliasedData {
    name: StringAliasedNodeData;
}

export type ConceptName = TileData<ConceptNameAlises>;

export interface DigitalObjectContentAliases extends AliasedData {
    content: FileListAliasedNodeData;
}

export type DigitalObjectContent = TileData<DigitalObjectContentAliases>;

export interface ConceptImagesAliases extends AliasedData {
    depicting_digital_asset_internal: ResourceInstanceListAliasedNodeData;
}

export type ConceptImages = TileData<ConceptImagesAliases>;

export interface DigitalObjectNameAliases extends AliasedData {
    name_content: StringAliasedNodeData;
}

export type DigitalObjectName = TileData<DigitalObjectNameAliases>;

export interface DigitalObjectInstanceAliases extends AliasedData {
    name?: DigitalObjectName;
    content?: DigitalObjectContent;
    statement?: ConceptStatement;
}

export type DigitalObjectInstance = ResourceData<DigitalObjectInstanceAliases>;

export type AppellativeStatus = TileData<AppellativeStatusAliases>;

export interface ConceptStatementAliases extends AliasedData {
    statement_content: StringAliasedNodeData;
    statement_language?: QuerysetsReferenceSelectFetchedOption;
    statement_type?: QuerysetsReferenceSelectFetchedOption;
    statement_type_metatype?: QuerysetsReferenceSelectFetchedOption;
    statement_data_assignment_object_used?: ResourceInstanceListAliasedNodeData;
    statement_data_assignment_actor?: ResourceInstanceListAliasedNodeData;
    statement_data_assignment_type?: QuerysetsReferenceSelectFetchedOption;
    statement_data_assignment_timespan_begin_of_the_begin?: StringAliasedNodeData | null;
    statement_data_assignment_timespan_end_of_the_end?: StringAliasedNodeData | null;
}

export type ConceptStatement = TileData<ConceptStatementAliases>;

export interface ConceptRelationAliases extends AliasedData {
    relation_status_ascribed_comparate: ResourceInstanceListAliasedNodeData;
    relation_status_ascribed_relation: QuerysetsReferenceSelectFetchedOption;
    relation_status_status: QuerysetsReferenceSelectFetchedOption;
    relation_status_status_metatype: QuerysetsReferenceSelectFetchedOption;
    relation_status_timespan_begin_of_the_begin: StringAliasedNodeData;
    relation_status_timespan_end_of_the_end: StringAliasedNodeData;
    relation_status_data_assignment_actor: ResourceInstanceListAliasedNodeData;
    relation_status_data_assignment_object_used: ResourceInstanceListAliasedNodeData;
    relation_status_data_assignment_type: QuerysetsReferenceSelectFetchedOption;
}

export type ConceptRelationStatus = TileData<ConceptRelationAliases>;

export interface ConceptMatchAliases extends AliasedData {
    match_status_ascribed_comparate: StringAliasedNodeData;
    match_status_ascribed_relation: QuerysetsReferenceSelectFetchedOption;
    match_status_status: QuerysetsReferenceSelectFetchedOption;
    match_status_status_metatype: QuerysetsReferenceSelectFetchedOption;
    match_status_timespan_begin_of_the_begin: StringAliasedNodeData;
    match_status_timespan_end_of_the_end: StringAliasedNodeData;
    match_status_data_assignment_actor: ResourceInstanceListAliasedNodeData;
    match_status_data_assignment_object_used: ResourceInstanceListAliasedNodeData;
    match_status_data_assignment_type: QuerysetsReferenceSelectFetchedOption;
}

export type ConceptMatchStatus = TileData<ConceptMatchAliases>;

export interface ConceptClassificationStatusAliases extends AliasedData {
    classification_status_ascribed_classification: ResourceInstanceListAliasedNodeData;
    classification_status_ascribed_relation: ReferenceSelectTreeNode[];
    classification_status_data_assignment_actor: ResourceInstanceListAliasedNodeData;
    classification_status_data_assignment_object_used: ResourceInstanceListAliasedNodeData;
    classification_status_data_assignment_type: ReferenceSelectTreeNode[];
    classification_status_timespan_begin_of_the_begin: string;
    classification_status_timespan_end_of_the_end: string;
    classification_status_type: ReferenceSelectTreeNode[];
    classification_status_type_metatype: ReferenceSelectTreeNode[];
}

export type ConceptClassificationStatus =
    TileData<ConceptClassificationStatusAliases>;

export interface ConceptTypeAliases extends AliasedData {
    type: QuerysetsReferenceSelectFetchedOption;
    metatype?: QuerysetsReferenceSelectFetchedOption;
}

export type ConceptType = TileData<ConceptTypeAliases>;

export interface IdentifierAliases extends AliasedData {
    identifier_content: StringAliasedNodeData;
    identifier_label?: StringAliasedNodeData;
    identifier_type?: QuerysetsReferenceSelectFetchedOption;
    identifier_type_metatype?: QuerysetsReferenceSelectFetchedOption;
}

export type Identifier = TileData<IdentifierAliases>;

export interface SchemeStatementAliases extends AliasedData {
    statement_content: StringAliasedNodeData;
    statement_language?: QuerysetsReferenceSelectFetchedOption;
    statement_type?: QuerysetsReferenceSelectFetchedOption;
    statement_type_metatype?: QuerysetsReferenceSelectFetchedOption;
    statement_data_assignment_object_used?: ResourceInstanceListAliasedNodeData;
    statement_data_assignment_actor?: ResourceInstanceListAliasedNodeData;
    statement_data_assignment_type?: QuerysetsReferenceSelectFetchedOption;
    statement_data_assignment_timespan_begin_of_the_begin?: StringAliasedNodeData | null;
    statement_data_assignment_timespan_end_of_the_end?: StringAliasedNodeData | null;
}

export type SchemeStatement = TileData<SchemeStatementAliases>;

export interface SchemeRightsAliases extends TileData {
    right_holder?: ResourceInstanceListAliasedNodeData;
    right_type?: QuerysetsReferenceSelectFetchedOption;
    right_statement?: SchemeRightStatement;
}

export type SchemeRights = TileData<SchemeRightsAliases>;

export interface SchemeRightStatementAliases extends AliasedData {
    right_statement_content?: StringAliasedNodeData;
    right_statement_label?: StringAliasedNodeData;
    right_statement_language?: QuerysetsReferenceSelectFetchedOption;
    right_statement_type?: QuerysetsReferenceSelectFetchedOption;
    right_statement_type_metatype?: QuerysetsReferenceSelectFetchedOption;
}

export type SchemeRightStatement = TileData<SchemeRightStatementAliases>;

export interface SchemeNamespaceAliases extends AliasedData {
    namespace_name: StringAliasedNodeData;
    namespace_type: QuerysetsReferenceSelectFetchedOption;
}

export type SchemeNamespace = TileData<SchemeNamespaceAliases>;

export interface SchemeCreationAliases extends AliasedData {
    creation_sources: ResourceInstanceListAliasedNodeData;
}

export type SchemeCreation = TileData<SchemeCreationAliases>;

export interface ConceptInstance {
    aliased_data: {
        appellative_status?: AppellativeStatus[];
        concept_statement?: ConceptStatement[];
        depicting_digital_asset_internal?: ConceptImages;
        classification_status?: ConceptClassificationStatusAliases[];
    };
}

export interface ConceptClassificationStatusAliases extends AliasedData {
    aliased_data: {
        classification_status_ascribed_classification?: ResourceInstanceListAliasedNodeData;
        classification_status_ascribed_relation?: QuerysetsReferenceSelectFetchedOption;
        classification_status_data_assignment_actor?: ResourceInstanceListAliasedNodeData;
        classification_status_data_assignment_object_used?: ResourceInstanceListAliasedNodeData;
        classification_status_data_assignment_type?: QuerysetsReferenceSelectFetchedOption;
        classification_status_timespan_end_of_the_end?: StringAliasedNodeData | null;
        classification_status_timespan_begin_of_the_begin?: StringAliasedNodeData | null;
        classification_status_type?: QuerysetsReferenceSelectFetchedOption;
        classification_status_type_metatype?: QuerysetsReferenceSelectFetchedOption;
    };
}

export interface ConceptHeaderData {
    uri?: string;
    name?: string;
    descriptor?: ResourceDescriptor;
    principalUser?: number | string;
    lifeCycleState: string;
    partOfScheme?: ResourceInstanceListAliasedNodeData;
    schemeLabel?: string;
    parentConcepts?: ResourceInstanceReference[];
    type?: ReferenceSelectTreeNode[];
    status?: ReferenceSelectTreeNode[];
    identifier?: string;
}

export interface SchemeHeader {
    uri?: string;
    name?: string;
    descriptor?: ResourceDescriptor;
    principalUser?: number | string;
    lifeCycleState: string;
    identifier?: string;
}

export interface LanguageLabelCount {
    language: string;
    code: string;
    count: number;
}

export interface SchemeInstance {
    aliased_data: {
        namespace?: SchemeNamespace;
        creation?: SchemeCreation;
        appellative_status?: AppellativeStatus[];
        statement?: SchemeStatement[];
        rights?: SchemeRights;
    };
}

export interface ResourceDescriptor {
    name: string;
    description: string;
    language: string;
}

export interface NodeAndParentInstruction {
    node: TreeNode;
    shouldHideSiblings: boolean;
}

export interface IconLabels {
    concept: string;
    guideTerm: string;
    scheme: string;
    topConcept: string;
}

export interface SideNavMenuItem extends MenuItem {
    component?: Component;
    showIconIfCollapsed?: boolean;
}

export interface SearchResultItem {
    id: string;
    labels: Label[];
    label?: string;
    parents: {
        id: string;
        labels: Label[];
    }[][];
    polyhierarchical: boolean;
    guide_term?: boolean;
    top_concept?: boolean;
    resource_instance_lifecycle_state_id?: string;
    resource_instance_lifecycle_state_name?: string;
}

export interface SearchResultHierarchy {
    tileid?: string;
    searchResults: SearchResultItem[];
    isTopConcept?: boolean;
}

export interface archesPreset {
    arches: {
        legacy: {
            sidebar: string;
        };
        blue: string;
        green: string;
        red: string;
    };
}

export interface Notification {
    id: string;
    created: string;
    isread: boolean;
    message: string;
    recipient_id: string;
    link?: string; // pk for a SearchExportHistory instance
    files?: Array<{
        fileid: string;
        name: string;
        url: string;
    }>;
}

export interface PaginatorDetails {
    current_page: number;
    total_pages: number;
    results_per_page: number;
    has_next: boolean;
    total_notifications: number;
    unread_notifications: number;
}

export interface LifecycleState {
    id: string;
    name: string;
}

export interface ResourceInstanceLifecycleState {
    id: string;
    name: string;
    action_label: string;
    can_edit_resource_instances?: boolean;
    can_delete_resource_instances?: boolean;
    next_resource_instance_lifecycle_states?: ResourceInstanceLifecycleState[];
    previous_resource_instance_lifecycle_states?: ResourceInstanceLifecycleState[];
}

export interface EditLogEntry {
    editlogid: string;
    transactionid: string | null;
    edittype: string;
    edittype_label: string;
    timestamp: string;
    userid: string;
    user_firstname: string;
    user_lastname: string;
    user_username: string;
    user_email: string;
    nodegroupid: string | null;
    tileinstanceid: string | null;
    card_name: string | null;
    note: string | null;
}

export type SearchOperator = "and" | "or";

export type MatchMode =
    | "contains"
    | "exact"
    | "starts_with"
    | "ends_with"
    | "exists";

export type FacetType =
    | "label"
    | "note"
    | "language"
    | "concept_type"
    | "relationship_hierarchical"
    | "relationship_associated"
    | "match_uri"
    | "scheme"
    | "top_concept"
    | "uri"
    | "identifier"
    | "lifecycle_state"
    | "concept_set"
    | "attribution_source"
    | "attribution_contributor";

export interface SearchCondition {
    id: string;
    facet: FacetType;
    value: string;
    label_type?: string;
    note_type?: string;
    language?: string;
    direction?: "broader" | "narrower";
    cascade?: boolean;
    match_mode?: MatchMode;
    negated?: boolean;
}

export interface SearchGroup {
    id: string;
    operator: SearchOperator;
    conditions: (SearchCondition | SearchGroup)[];
}

export interface AdvancedSearchQuery {
    operator: SearchOperator;
    conditions: (SearchCondition | SearchGroup)[];
}

interface AdvancedSearchResultItem extends SearchResultItem {
    uri?: string | null;
    identifier?: string | null;
    notes: { content: string; language: string; type: string }[];
}

export interface AdvancedSearchResponse {
    current_page: number;
    total_pages: number;
    results_per_page: number;
    total_results: number;
    data: AdvancedSearchResultItem[];
}

export interface SchemeOption {
    id: string;
    labels: Label[];
}

export interface ControlledListOption {
    label: string;
    value: string;
}

export interface AdvancedSearchOptions {
    languages: { code: string; name: string }[];
    schemes: SchemeOption[];
    lifecycle_states: { id: string; name: string }[];
    label_types: ControlledListOption[];
    note_types: ControlledListOption[];
    concept_types: ControlledListOption[];
}

export interface SavedSearchItem {
    id: number;
    name: string;
    query: AdvancedSearchQuery;
    created: string;
    updated: string;
}

export interface ConceptSetItem {
    id: number;
    name: string;
    description: string;
    member_count: number;
    created: string;
    updated: string;
}

export interface ConceptSetDetail extends ConceptSetItem {
    members: SearchResultItem[];
}

export type DeleteConceptStrategy = "reparent" | "delete_children" | "orphan";
