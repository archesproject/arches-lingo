// Backport of core 8.2's file-list types (arches#13094). arches-vue-components
// 2.0.x types the metadata as plain strings, but Arches stores it per
// language. Remove this directory when Lingo moves to Arches 8.2 (Lingo 1.3).
import type {
    AliasedNodeData,
    CardXNodeXWidgetData,
} from "@/arches_vue_components/types.ts";
import type { LanguageValue } from "@/arches_vue_components/datatypes/string/types.ts";
import type { FILE_METADATA_FIELDS } from "@/arches_lingo/components/widgets/FileListMetadataWidget/constants.ts";

export type FileMetadataField = (typeof FILE_METADATA_FIELDS)[number];
export type FileMetadata = Record<
    FileMetadataField,
    Record<string, LanguageValue>
>;

export interface FileReference {
    url: string;
    name: string;
    path: string;
    size: number;
    type: string;
    index: number;
    width: number;
    height: number;
    status: string;
    content: string;
    file_id: string;
    accepted: boolean;
    lastModified: number;
    altText?: Record<string, LanguageValue>;
    attribution?: Record<string, LanguageValue>;
    description?: Record<string, LanguageValue>;
    title?: Record<string, LanguageValue>;
}

// Mirrors CardXNodeXWidgetData.visible. A consumer flips the bit on a copy
// of the widget data to show or hide part of the metadata editor.
export interface FileMetadataVisibilityConfig {
    visible: boolean;
}

export interface FileListCardXNodeXWidgetData extends CardXNodeXWidgetData {
    config: CardXNodeXWidgetData["config"] & {
        acceptedFiles: string;
        maxFiles: number;
        maxFilesize: number;
        rerender: boolean;
        label: string;
        // A field without an entry is shown.
        metadataFields?: Partial<
            Record<FileMetadataField, FileMetadataVisibilityConfig>
        >;
        // Without an entry the picker is hidden and metadata is edited in
        // the initial language, as in the Knockout file widget.
        metadataLanguageSelect?: FileMetadataVisibilityConfig;
    };
}

export interface FileListAliasedNodeData extends AliasedNodeData {
    node_value: FileReference[] | null;
    details: never[];
}

export interface FileData extends Partial<FileMetadata> {
    name: string;
    size: number;
    type: string;
    url: string;
    file: File;
    node_id: string;
}

export type PrimeVueFile = File & { objectURL: string };
