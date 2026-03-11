export interface EtlModule {
    name: string | null;
    etl_type: string | null;
}

export interface LoadEventTask {
    loadid: string;
    status: string | null;
    complete: boolean;
    successful: boolean | null;
    load_description: string | null;
    load_details: Record<string, unknown> | null;
    error_message: string | null;
    load_start_time: string | null;
    load_end_time: string | null;
    etl_module: EtlModule;
}

export interface TaskPaginator {
    total: number;
    total_pages: number;
    current_page: number;
    has_next: boolean;
    has_previous: boolean;
}

export interface UserTasksResponse {
    events: LoadEventTask[];
    paginator: TaskPaginator;
}
