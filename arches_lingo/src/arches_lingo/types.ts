import type { Ref } from "vue";

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

export interface Concept {
    id: string;
    labels: {
        language: string;
        value: string;
        valuetype: string;
    }[];
    parents: {
        id: string;
        labels: {
            language: string;
            value: string;
            valuetype: string;
        }[];
    }[];
    polyhierarchical: boolean;
}
