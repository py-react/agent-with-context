

export type ExecuteToolRequest = {
	tool_name: string;
	parameters?: Record<string, unknown> | null;
};

