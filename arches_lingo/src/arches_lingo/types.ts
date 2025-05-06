import type { Ref } from "vue";
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
    resourceinstanceid: string;
    aliased_data: T;
}

export interface AppellativeStatusAliases extends AliasedData {
    appellative_status_ascribed_name_content: string;
    appellative_status_ascribed_name_language?: ReferenceSelectFetchedOption[];
    appellative_status_ascribed_relation?: ReferenceSelectFetchedOption[];
    appellative_status_status_metatype?: ReferenceSelectFetchedOption[];
    appellative_status_status?: ReferenceSelectFetchedOption[];
    appellative_status_data_assignment_object_used: ResourceInstanceReference[];
    appellative_status_data_assignment_actor: ResourceInstanceReference[];
    appellative_status_data_assignment_type: ReferenceSelectFetchedOption[];
    appellative_status_timespan_begin_of_the_begin: string;
    appellative_status_timespan_end_of_the_end: string;
}

export interface ConceptNameAlises extends AliasedData {
    name: string;
}

export type ConceptName = TileData<ConceptNameAlises>;

export interface DigitalObjectContentAliases extends AliasedData {
    content: FileReference[];
}

export type DigitalObjectContent = TileData<DigitalObjectContentAliases>;

export interface ConceptImagesAliases extends AliasedData {
    depicting_digital_asset_internal: ResourceInstanceReference[];
}

export type ConceptImages = TileData<ConceptImagesAliases>;

export interface DigitalObjectNameAliases extends AliasedData {
    name_content: string;
}

export type DigitalObjectName = TileData<DigitalObjectNameAliases>;

export interface DigitalObjectInstanceAliases extends AliasedData {
    name: DigitalObjectName;
    content?: DigitalObjectContent;
    resourceinstanceid: string;
    statement?: ConceptStatement;
}

export type DigitalObjectInstance = ResourceData<DigitalObjectInstanceAliases>;

export type AppellativeStatus = TileData<AppellativeStatusAliases>;

export interface ConceptStatementAliases extends AliasedData {
    statement_content: string;
    statement_language?: ReferenceSelectFetchedOption[];
    statement_type?: ReferenceSelectFetchedOption[];
    statement_type_metatype?: ReferenceSelectFetchedOption[];
    statement_data_assignment_object_used?: ResourceInstanceReference[];
    statement_data_assignment_actor?: ResourceInstanceReference[];
    statement_data_assignment_type?: ReferenceSelectFetchedOption[];
    statement_data_assignment_timespan_begin_of_the_begin?: string | null;
    statement_data_assignment_timespan_end_of_the_end?: string | null;
}

export type ConceptStatement = TileData<ConceptStatementAliases>;

export interface SchemeStatementAliases extends AliasedData {
    statement_content_n1: string;
    statement_language_n1?: ReferenceSelectFetchedOption[];
    statement_type_n1?: ReferenceSelectFetchedOption[];
    statement_type_metatype_n1?: ReferenceSelectFetchedOption[];
    statement_data_assignment_object_used?: ResourceInstanceReference[];
    statement_data_assignment_actor?: ResourceInstanceReference[];
    statement_data_assignment_type?: ReferenceSelectFetchedOption[];
    statement_data_assignment_timespan_begin_of_the_begin?: string | null;
    statement_data_assignment_timespan_end_of_the_end?: string | null;
}

export type SchemeStatement = TileData<SchemeStatementAliases>;

export interface SchemeRightsAliases extends TileData {
    right_holder?: ResourceInstanceReference[];
    right_type?: ReferenceSelectFetchedOption[];
    right_statement?: SchemeRightStatement;
}

export type SchemeRights = TileData<SchemeRightsAliases>;

export interface SchemeRightStatementAliases extends AliasedData {
    right_statement_content?: string;
    right_statement_label?: string;
    right_statement_language?: ReferenceSelectFetchedOption[];
    right_statement_type?: ReferenceSelectFetchedOption[];
    right_statement_type_metatype?: ReferenceSelectFetchedOption[];
}

export type SchemeRightStatement = TileData<SchemeRightStatementAliases>;

export interface SchemeNamespaceAliases extends AliasedData {
    namespace_name: string;
    namespace_type: ReferenceSelectFetchedOption[];
}

export type SchemeNamespace = TileData<SchemeNamespaceAliases>;

export interface SchemeCreationAliases extends AliasedData {
    creation_sources: ResourceInstanceReference[];
}

export type SchemeCreation = TileData<SchemeCreationAliases>;

export interface ConceptInstance {
    aliased_data: {
        appellative_status?: AppellativeStatus[];
        concept_statement?: ConceptStatement[];
        depicting_digital_asset_internal?: ConceptImages[];
        classification_status?: ConceptClassificationStatusAliases[];
    };
}

export interface ConceptClassificationStatusAliases extends AliasedData {
    aliased_data: {
        classification_status_ascribed_classification?: ResourceInstanceReference[];
        classification_status_ascribed_relation?: ReferenceSelectFetchedOption[];
        classification_status_data_assignment_actor?: ResourceInstanceReference[];
        classification_status_data_assignment_object_used?: ResourceInstanceReference[];
        classification_status_data_assignment_type?: ReferenceSelectFetchedOption[];
        classification_status_timespan_end_of_the_end?: string | null;
        classification_status_timespan_begin_of_the_begin?: string | null;
        classification_status_type?: ReferenceSelectFetchedOption[];
        classification_status_type_metatype?: ReferenceSelectFetchedOption[];
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

export interface SearchResultItem {
    id: string;
    labels: Label[];
    parents: {
        id: string;
        labels: Label[];
    }[];
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
