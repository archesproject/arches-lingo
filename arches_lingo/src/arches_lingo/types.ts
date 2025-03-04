import type { Ref } from "vue";
import type { TreeNode } from "primevue/treenode";
import type { Label } from "@/arches_vue_utils/types.ts";
import type { EDIT, VIEW } from "@/arches_lingo/constants.ts";
import type { ControlledListItem } from "@/arches_controlled_lists/types.ts";

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
    items: ControlledListItem[];
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

export interface ResourceInstanceReference {
    resourceId: string;
    ontologyProperty: string;
    resourceXresourceId?: string;
    inverseOntologyProperty: string;
    display_value?: string;
}

export interface ResourceInstanceResult {
    resourceinstanceid: string;
    descriptors: { [key: string]: { name: string } };
}

export type DataComponentMode = typeof EDIT | typeof VIEW;

export interface MetaStringText {
    name: string;
    type: string;
    language: string;
    deleteConfirm: string;
    noRecords: string;
}

export interface AppellativeStatus {
    resourceinstance?: string;
    tileid?: string;
    appellative_status_ascribed_name_content: string;
    appellative_status_ascribed_name_language?: ControlledListItem[];
    appellative_status_ascribed_relation?: ControlledListItem[];
    appellative_status_status_metatype?: ControlledListItem[];
    appellative_status_status?: ControlledListItem[];
    appellative_status_data_assignment_object_used: ResourceInstanceReference[];
    appellative_status_data_assignment_actor: ResourceInstanceReference[];
    appellative_status_data_assignment_type: ControlledListItem[];
    appellative_status_timespan_begin_of_the_begin: string;
    appellative_status_timespan_end_of_the_end: string;
}

export interface SchemeStatement {
    resourceinstance?: string;
    tileid?: string;
    statement_content_n1: string;
    statement_language_n1?: ControlledListItem[];
    statement_type_n1?: ControlledListItem[];
    statement_type_metatype_n1?: ControlledListItem[];
    statement_data_assignment_object_used: ResourceInstanceReference[];
    statement_data_assignment_actor: ResourceInstanceReference[];
    statement_data_assignment_type: ControlledListItem[];
    statement_data_assignment_timespan_begin_of_the_begin: string;
    statement_data_assignment_timespan_end_of_the_end: string;
}

export interface SchemeRights {
    tileid?: string;
    right_holder?: ResourceInstanceReference[];
    right_type?: ControlledListItem[];
    right_statement?: SchemeRightStatement;
}

export interface SchemeRightStatement {
    tileid?: string;
    right_statement_content?: string;
    right_statement_label?: string;
    right_statement_language?: ControlledListItem[];
    right_statement_type?: ControlledListItem[];
    right_statement_type_metatype?: ControlledListItem[];
}

export interface SchemeNamespace {
    resourceinstance?: string;
    tileid?: string;
    namespace_name: string;
    namespace_type: ControlledListItem[];
}

export interface SchemeCreation {
    resourceinstance?: string;
    tileid?: string;
    creation_sources: ResourceInstanceReference[];
}

export type SchemeTile =
    | AppellativeStatus
    | SchemeStatement
    | SchemeNamespace
    | SchemeCreation
    | SchemeRights;

export interface SchemeInstance {
    namespace?: SchemeNamespace;
    creation?: SchemeCreation;
    appellative_status?: AppellativeStatus[];
    statement?: SchemeStatement[];
    rights?: SchemeRights;
}

export interface SchemeResource {
    resourceinstanceid: string;
    descriptors: {
        [key: string]: {
            name: string;
            description: string;
        };
    };
}

export interface ResourceDescriptor {
    name: string;
    description: string;
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
