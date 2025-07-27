

export type ChatRequest = {
	message: string;
	session_id?: string | null;
	stream?: boolean | null;
};

