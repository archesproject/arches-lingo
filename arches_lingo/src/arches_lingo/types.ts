import type { Component, Ref } from "vue";
import type { MenuItem } from "primevue/menuitem";
import type { TreeNode } from "primevue/treenode";
import type { Label } from "@/arches_component_lab/types.ts";
import type { EDIT, VIEW } from "@/arches_lingo/constants.ts";
import type { ReferenceSelectFetchedOption } from "@/arches_controlled_lists/widgets/types.ts";
import type {
    ResourceInstanceReference,
    FileReference,
} from "@/arches_component_lab/widgets/types.ts";

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
    items: ReferenceSelectFetchedOption[];
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
    language: string;
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

interface QuerysetsString {
    display_value: string;
    interchange_value: string;
}

interface QuerysetsReferenceSelectFetchedOption {
    display_value: string;
    interchange_value: ReferenceSelectFetchedOption[];
}

interface QuerysetsResourceInstanceReference {
    display_value: string;
    interchange_value: ResourceInstanceReference[];
}

export interface AppellativeStatusAliases extends AliasedData {
    appellative_status_ascribed_name_content: QuerysetsString;
    appellative_status_ascribed_name_language?: QuerysetsReferenceSelectFetchedOption;
    appellative_status_ascribed_relation?: QuerysetsReferenceSelectFetchedOption;
    appellative_status_status_metatype?: QuerysetsReferenceSelectFetchedOption;
    appellative_status_status?: QuerysetsReferenceSelectFetchedOption;
    appellative_status_data_assignment_object_used: QuerysetsResourceInstanceReference;
    appellative_status_data_assignment_actor: QuerysetsResourceInstanceReference;
    appellative_status_data_assignment_type: QuerysetsReferenceSelectFetchedOption;
    appellative_status_timespan_begin_of_the_begin: QuerysetsString;
    appellative_status_timespan_end_of_the_end: QuerysetsString;
}

export interface ConceptNameAlises extends AliasedData {
    name: QuerysetsString;
}

export type ConceptName = TileData<ConceptNameAlises>;

interface QuerysetsFileReference {
    display_value: string;
    interchange_value: FileReference[];
}

export interface DigitalObjectContentAliases extends AliasedData {
    content: QuerysetsFileReference[];
}

export type DigitalObjectContent = TileData<DigitalObjectContentAliases>;

export interface ConceptImagesAliases extends AliasedData {
    depicting_digital_asset_internal: QuerysetsResourceInstanceReference;
}

export type ConceptImages = TileData<ConceptImagesAliases>;

export interface DigitalObjectNameAliases extends AliasedData {
    name_content: QuerysetsString;
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
    statement_content: QuerysetsString;
    statement_language?: QuerysetsReferenceSelectFetchedOption;
    statement_type?: QuerysetsReferenceSelectFetchedOption;
    statement_type_metatype?: QuerysetsReferenceSelectFetchedOption;
    statement_data_assignment_object_used?: QuerysetsResourceInstanceReference;
    statement_data_assignment_actor?: QuerysetsResourceInstanceReference;
    statement_data_assignment_type?: QuerysetsReferenceSelectFetchedOption;
    statement_data_assignment_timespan_begin_of_the_begin?: QuerysetsString | null;
    statement_data_assignment_timespan_end_of_the_end?: QuerysetsString | null;
}

export type ConceptStatement = TileData<ConceptStatementAliases>;

export interface SchemeStatementAliases extends AliasedData {
    statement_content_n1: QuerysetsString;
    statement_language_n1?: QuerysetsReferenceSelectFetchedOption;
    statement_type_n1?: QuerysetsReferenceSelectFetchedOption;
    statement_type_metatype_n1?: QuerysetsReferenceSelectFetchedOption;
    statement_data_assignment_object_used?: QuerysetsResourceInstanceReference;
    statement_data_assignment_actor?: QuerysetsResourceInstanceReference;
    statement_data_assignment_type?: QuerysetsReferenceSelectFetchedOption;
    statement_data_assignment_timespan_begin_of_the_begin?: QuerysetsString | null;
    statement_data_assignment_timespan_end_of_the_end?: QuerysetsString | null;
}

export type SchemeStatement = TileData<SchemeStatementAliases>;

export interface SchemeRightsAliases extends TileData {
    right_holder?: QuerysetsResourceInstanceReference;
    right_type?: QuerysetsReferenceSelectFetchedOption;
    right_statement?: SchemeRightStatement;
}

export type SchemeRights = TileData<SchemeRightsAliases>;

export interface SchemeRightStatementAliases extends AliasedData {
    right_statement_content?: QuerysetsString;
    right_statement_label?: QuerysetsString;
    right_statement_language?: QuerysetsReferenceSelectFetchedOption;
    right_statement_type?: QuerysetsReferenceSelectFetchedOption;
    right_statement_type_metatype?: QuerysetsReferenceSelectFetchedOption;
}

export type SchemeRightStatement = TileData<SchemeRightStatementAliases>;

export interface SchemeNamespaceAliases extends AliasedData {
    namespace_name: QuerysetsString;
    namespace_type: QuerysetsReferenceSelectFetchedOption;
}

export type SchemeNamespace = TileData<SchemeNamespaceAliases>;

export interface SchemeCreationAliases extends AliasedData {
    creation_sources: QuerysetsResourceInstanceReference;
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
        classification_status_ascribed_classification?: QuerysetsResourceInstanceReference;
        classification_status_ascribed_relation?: QuerysetsReferenceSelectFetchedOption;
        classification_status_data_assignment_actor?: QuerysetsResourceInstanceReference;
        classification_status_data_assignment_object_used?: QuerysetsResourceInstanceReference;
        classification_status_data_assignment_type?: QuerysetsReferenceSelectFetchedOption;
        classification_status_timespan_end_of_the_end?: QuerysetsString | null;
        classification_status_timespan_begin_of_the_begin?: QuerysetsString | null;
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
    partOfScheme?: ResourceInstanceReference[];
    parentConcepts?: ResourceInstanceReference[];
    type?: ReferenceSelectFetchedOption[];
    status?: ReferenceSelectFetchedOption[];
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
    parents: {
        id: string;
        labels: Label[];
    }[][];
    polyhierarchical: boolean;
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
