import type { Ref } from "vue";
import type { TreeNode } from "primevue/treenode";
import type { Label } from "@/arches_vue_utils/types.ts";
import type { EDIT, VIEW } from "./constants";
import SchemeNamespace from "@/arches_lingo/src/arches_lingo/components/scheme/report/SchemeNamespace.vue";
import SchemeLabel from "@/arches_lingo/src/arches_lingo/components/scheme/report/SchemeLabel.vue";
import SchemeLicense from "@/arches_lingo/src/arches_lingo/components/scheme/report/SchemeLicense.vue";
import SchemeStandard from "@/arches_lingo/src/arches_lingo/components/scheme/report/SchemeStandard.vue";
import SchemeAuthority from "@/arches_lingo/src/arches_lingo/components/scheme/report/SchemeAuthority.vue";
import SchemeNote from "@/arches_lingo/src/arches_lingo/components/scheme/report/SchemeNote.vue";

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

export interface ControlledListeItemLabelValue {
    id: string;
    valuetype_id: string;
    language_id: string;
    value: string;
    list_item_id: string;
}

export interface ControlledListItem {
    item_id?: string;
    list_id: string;
    uri: string;
    sortorder?: number;
    guide?: boolean;
    labels: ControlledListeItemLabelValue[];
}

export interface ControlledListItemResult {
    id?: string;
    list_id: string;
    uri: string;
    sortorder?: number;
    guide?: boolean;
    values: ControlledListeItemLabelValue[];
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
interface ControlledListItemValue {
    value: string;
}

export type SectionTypes =
    | typeof SchemeLabel
    | typeof SchemeNamespace
    | typeof SchemeLicense
    | typeof SchemeStandard
    | typeof SchemeAuthority
    | typeof SchemeNote;

export type DataComponentMode = typeof EDIT | typeof VIEW;

export interface SchemeNamespaceUpdate {
    namespace?: {
        namespace_name: string;
        namespace_type: ControlledListItemValue[] | ControlledListItem[];
    };
}

export interface MetaString {
    tileid: string;
}

export interface MetaStringText {
    name: string;
    type: string;
    language: string;
    deleteConfirm: string;
    noRecords: string;
}

export interface AppellativeStatus {
    tileid: string;
    appellative_status_ascribed_name_content: string;
    appellative_status_ascribed_name_language?: ControlledListItem[];
    appellative_status_ascribed_relation?: ControlledListItem[];
    appellative_status_status_metatype?: ControlledListItem[];
    appellative_status_status?: ControlledListItem[];
    appellative_status_data_assignment_object_used: ResourceInstanceReference[];
    appellative_status_data_assignment_actor: ResourceInstanceReference[];
    appellative_status_data_assignment_type: ControlledListItem[];
}

export interface SchemeStatement {
    tileid: string;
    statement_content_n1: string;
    statement_language_n1?: ControlledListItem[];
    statement_type_n1?: ControlledListItem[];
    statement_data_assignment_object_used: ResourceInstanceReference[];
    statement_data_assignment_actor: ResourceInstanceReference[];
}

export interface SchemeInstance {
    namespace?: {
        namespace_name: string;
        namespace_type: ControlledListItem[];
    };
    creation?: {
        creation_sources: ResourceInstanceReference[];
    };
    appellative_status?: AppellativeStatus[];
    statement?: SchemeStatement[];
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
