import type { Component, Ref } from "vue";
import type { MenuItem } from "primevue/menuitem";
import type { TreeNode } from "primevue/treenode";
import type { EDIT, VIEW } from "@/arches_lingo/constants.ts";

import type { ReferenceSelectTreeNode } from "@/arches_controlled_lists/datatypes/reference-select/types.ts";
import type { Label } from "@/arches_controlled_lists/types.ts";

import type { StringValue } from "@/arches_component_lab/datatypes/string/types.ts";
import type { ResourceInstanceListValue } from "@/arches_component_lab/datatypes/resource-instance-list/types.ts";
import type { FileListValue } from "@/arches_component_lab/datatypes/file-list/types.ts";

export interface User {
    first_name: string;
    last_name: string;
    username: string;
    email: string;
}

// Prop injection types
export interface UserRefAndSetter {
    user: Ref<User | null>;
    setUser: (userToSet: User | null) => void;
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
}

export interface Scheme {
    id: string;
    labels: Label[];
    top_concepts: Concept[];
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
    resource_instance_lifecycle_state?: string;
}

export type DataComponentMode = typeof EDIT | typeof VIEW;

export interface MetaStringText {
    name: string;
    type: string;
    language?: string;
    deleteConfirm: string;
    noRecords: string;
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
}

export interface AppellativeStatusAliases extends AliasedData {
    appellative_status_ascribed_name_content: StringValue;
    appellative_status_ascribed_name_language?: QuerysetsReferenceSelectFetchedOption;
    appellative_status_ascribed_relation?: QuerysetsReferenceSelectFetchedOption;
    appellative_status_status_metatype?: QuerysetsReferenceSelectFetchedOption;
    appellative_status_status?: QuerysetsReferenceSelectFetchedOption;
    appellative_status_data_assignment_object_used: ResourceInstanceListValue;
    appellative_status_data_assignment_actor: ResourceInstanceListValue;
    appellative_status_data_assignment_type: QuerysetsReferenceSelectFetchedOption;
    appellative_status_timespan_begin_of_the_begin: StringValue;
    appellative_status_timespan_end_of_the_end: StringValue;
}

export interface ConceptNameAlises extends AliasedData {
    name: StringValue;
}

export type ConceptName = TileData<ConceptNameAlises>;

export interface DigitalObjectContentAliases extends AliasedData {
    content: FileListValue[];
}

export type DigitalObjectContent = TileData<DigitalObjectContentAliases>;

export interface ConceptImagesAliases extends AliasedData {
    depicting_digital_asset_internal: ResourceInstanceListValue;
}

export type ConceptImages = TileData<ConceptImagesAliases>;

export interface DigitalObjectNameAliases extends AliasedData {
    name_content: StringValue;
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
    statement_content: StringValue;
    statement_language?: QuerysetsReferenceSelectFetchedOption;
    statement_type?: QuerysetsReferenceSelectFetchedOption;
    statement_type_metatype?: QuerysetsReferenceSelectFetchedOption;
    statement_data_assignment_object_used?: ResourceInstanceListValue;
    statement_data_assignment_actor?: ResourceInstanceListValue;
    statement_data_assignment_type?: QuerysetsReferenceSelectFetchedOption;
    statement_data_assignment_timespan_begin_of_the_begin?: StringValue | null;
    statement_data_assignment_timespan_end_of_the_end?: StringValue | null;
}

export type ConceptStatement = TileData<ConceptStatementAliases>;

export interface ConceptRelationAliases extends AliasedData {
    relation_status_ascribed_comparate: ResourceInstanceListValue;
    relation_status_ascribed_relation: ReferenceSelectTreeNode[];
    relation_status_status: ReferenceSelectTreeNode[];
    relation_status_status_metatype: ReferenceSelectTreeNode[];
    relation_status_timespan_begin_of_the_begin: string;
    relation_status_timespan_end_of_the_end: string;
    relation_status_data_assignment_actor: ResourceInstanceListValue;
    relation_status_data_assignment_object_used: ResourceInstanceListValue;
    relation_status_data_assignment_type: ReferenceSelectTreeNode[];
}

export type ConceptRelationStatus = TileData<ConceptRelationAliases>;

export interface ConceptMatchAliases extends AliasedData {
    match_status_ascribed_comparate: StringValue;
    match_status_ascribed_relation: ReferenceSelectTreeNode[];
    match_status_status: ReferenceSelectTreeNode[];
    match_status_status_metatype: ReferenceSelectTreeNode[];
    match_status_timespan_begin_of_the_begin: string;
    match_status_timespan_end_of_the_end: string;
    match_status_data_assignment_actor: ResourceInstanceListValue;
    match_status_data_assignment_object_used: ResourceInstanceListValue;
    match_status_data_assignment_type: ReferenceSelectTreeNode[];
}

export type ConceptMatchStatus = TileData<ConceptMatchAliases>;

export interface ConceptClassificationStatusAliases extends AliasedData {
    classification_status_ascribed_classification: ResourceInstanceListValue;
    classification_status_ascribed_relation: ReferenceSelectTreeNode[];
    classification_status_data_assignment_actor: ResourceInstanceListValue;
    classification_status_data_assignment_object_used: ResourceInstanceListValue;
    classification_status_data_assignment_type: ReferenceSelectTreeNode[];
    classification_status_timespan_begin_of_the_begin: string;
    classification_status_timespan_end_of_the_end: string;
    classification_status_type: ReferenceSelectTreeNode[];
    classification_status_type_metatype: ReferenceSelectTreeNode[];
}

export type ConceptClassificationStatus =
    TileData<ConceptClassificationStatusAliases>;

export interface SchemeStatementAliases extends AliasedData {
    statement_content: StringValue;
    statement_language?: QuerysetsReferenceSelectFetchedOption;
    statement_type?: QuerysetsReferenceSelectFetchedOption;
    statement_type_metatype?: QuerysetsReferenceSelectFetchedOption;
    statement_data_assignment_object_used?: ResourceInstanceListValue;
    statement_data_assignment_actor?: ResourceInstanceListValue;
    statement_data_assignment_type?: QuerysetsReferenceSelectFetchedOption;
    statement_data_assignment_timespan_begin_of_the_begin?: StringValue | null;
    statement_data_assignment_timespan_end_of_the_end?: StringValue | null;
}

export type SchemeStatement = TileData<SchemeStatementAliases>;

export interface SchemeRightsAliases extends TileData {
    right_holder?: ResourceInstanceListValue;
    right_type?: QuerysetsReferenceSelectFetchedOption;
    right_statement?: SchemeRightStatement;
}

export type SchemeRights = TileData<SchemeRightsAliases>;

export interface SchemeRightStatementAliases extends AliasedData {
    right_statement_content?: StringValue;
    right_statement_label?: StringValue;
    right_statement_language?: QuerysetsReferenceSelectFetchedOption;
    right_statement_type?: QuerysetsReferenceSelectFetchedOption;
    right_statement_type_metatype?: QuerysetsReferenceSelectFetchedOption;
}

export type SchemeRightStatement = TileData<SchemeRightStatementAliases>;

export interface SchemeNamespaceAliases extends AliasedData {
    namespace_name: StringValue;
    namespace_type: QuerysetsReferenceSelectFetchedOption;
}

export type SchemeNamespace = TileData<SchemeNamespaceAliases>;

export interface SchemeCreationAliases extends AliasedData {
    creation_sources: ResourceInstanceListValue;
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
        classification_status_ascribed_classification?: ResourceInstanceListValue;
        classification_status_ascribed_relation?: QuerysetsReferenceSelectFetchedOption;
        classification_status_data_assignment_actor?: ResourceInstanceListValue;
        classification_status_data_assignment_object_used?: ResourceInstanceListValue;
        classification_status_data_assignment_type?: QuerysetsReferenceSelectFetchedOption;
        classification_status_timespan_end_of_the_end?: StringValue | null;
        classification_status_timespan_begin_of_the_begin?: StringValue | null;
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
    partOfScheme?: ResourceInstanceListValue;
    parentConcepts?: ResourceInstanceListValue[];
    type?: ReferenceSelectTreeNode[];
    status?: ReferenceSelectTreeNode[];
}

export interface SchemeHeader {
    uri?: string;
    name?: string;
    descriptor?: ResourceDescriptor;
    principalUser?: number | string;
    lifeCycleState: string;
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
    scheme: string;
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
