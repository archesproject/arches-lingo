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

export interface TileData {
    resourceinstance?: string;
    tileid?: string;
}

export interface AppellativeStatus extends TileData {
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

export interface ConceptStatement extends TileData {
    statement_content: string;
    statement_language?: ControlledListItem[];
    statement_type?: ControlledListItem[];
    statement_type_metatype?: ControlledListItem[];
    statement_data_assignment_object_used?: ResourceInstanceReference[];
    statement_data_assignment_actor?: ResourceInstanceReference[];
    statement_data_assignment_type?: ControlledListItem[];
    statement_data_assignment_timespan_begin_of_the_begin?: string | null;
    statement_data_assignment_timespan_end_of_the_end?: string | null;
}

export interface ConceptRelationStatus extends TileData {
    relation_status_ascribed_comparate: ResourceInstanceReference[];
    relation_status_ascribed_relation: ControlledListItem[];
    relation_status_status: ControlledListItem[];
    relation_status_status_metatype: ControlledListItem[];
    relation_status_timespan_begin_of_the_begin: string;
    relation_status_timespan_end_of_the_end: string;
    relation_status_data_assignment_actor: ResourceInstanceReference[];
    relation_status_data_assignment_object_used: ResourceInstanceReference[];
    relation_status_data_assignment_type: ControlledListItem[];
}

export interface ConceptMatchStatus extends TileData {
    match_status_ascribed_comparate: ResourceInstanceReference[];
    match_status_ascribed_relation: ControlledListItem[];
    match_status_status: ControlledListItem[];
    match_status_status_metatype: ControlledListItem[];
    match_status_timespan_begin_of_the_begin: string;
    match_status_timespan_end_of_the_end: string;
    match_status_data_assignment_actor: ResourceInstanceReference[];
    match_status_data_assignment_object_used: ResourceInstanceReference[];
    match_status_data_assignment_type: ControlledListItem[];
}

export interface SchemeStatement extends TileData {
    statement_content_n1: string;
    statement_language_n1?: ControlledListItem[];
    statement_type_n1?: ControlledListItem[];
    statement_type_metatype_n1?: ControlledListItem[];
    statement_data_assignment_object_used?: ResourceInstanceReference[];
    statement_data_assignment_actor?: ResourceInstanceReference[];
    statement_data_assignment_type?: ControlledListItem[];
    statement_data_assignment_timespan_begin_of_the_begin?: string | null;
    statement_data_assignment_timespan_end_of_the_end?: string | null;
}

export interface SchemeRights extends TileData {
    right_holder?: ResourceInstanceReference[];
    right_type?: ControlledListItem[];
    right_statement?: SchemeRightStatement;
}

export interface SchemeRightStatement extends TileData {
    right_statement_content?: string;
    right_statement_label?: string;
    right_statement_language?: ControlledListItem[];
    right_statement_type?: ControlledListItem[];
    right_statement_type_metatype?: ControlledListItem[];
}

export interface SchemeNamespace extends TileData {
    namespace_name: string;
    namespace_type: ControlledListItem[];
}

export interface SchemeCreation extends TileData {
    creation_sources: ResourceInstanceReference[];
}

export interface ConceptInstance {
    appellative_status?: AppellativeStatus[];
}

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
