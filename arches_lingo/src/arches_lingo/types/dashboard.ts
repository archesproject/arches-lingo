import type { Label } from "@/arches_controlled_lists/types.ts";
import type { SearchResultItem } from "@/arches_lingo/types.ts";

export interface DashboardActivityItem {
    editlogid: string;
    edittype: string;
    edittype_label: string;
    card_name: string | null;
    timestamp: string | null;
    user_username: string;
    user_firstname: string;
    user_lastname: string;
    resource_id: string;
    labels: Label[];
    resource_type: "concept" | "scheme";
}

export interface ConceptTypeCount {
    label: string;
    uri: string | null;
    count: number;
}

export interface LabelTypeCount {
    label: string;
    uri: string;
    count: number;
}

export interface LabelLanguageCount {
    language: string;
    code: string;
    count: number;
}

export interface DashboardStats {
    user_display_name: string;
    scheme_count: number;
    concept_count: number;
    concepts_by_type: ConceptTypeCount[];
    label_count: number;
    labels_per_concept: number;
    labels_by_type: LabelTypeCount[];
    labels_by_language: LabelLanguageCount[];
    recent_activity: DashboardActivityItem[];
}

export interface MissingTranslationsResponse {
    current_page: number;
    total_pages: number;
    results_per_page: number;
    total_results: number;
    data: SearchResultItem[];
}
