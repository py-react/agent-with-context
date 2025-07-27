import type { Body__api_agent_context_post } from '../models/Body__api_agent_context_post';
import type { Body__api_agent_context_put } from '../models/Body__api_agent_context_put';
import type { ChatRequest } from '../models/ChatRequest';
import type { CreateSessionRequest } from '../models/CreateSessionRequest';
import type { ExecuteToolRequest } from '../models/ExecuteToolRequest';
import type { SendMessageRequest } from '../models/SendMessageRequest';
import type { CancelablePromise } from '../core/CancelablePromise';
import { OpenAPI } from '../core/OpenAPI';
import { request as __request } from '../core/request';

export type TDataApiAgentGet = {
                sessionId: string
            }
export type TDataApiAgentPost = {
                requestBody: CreateSessionRequest
            }
export type TDataApiAgentDelete = {
                sessionId: string
            }
export type TDataApiAgentContextGet = {
                fileId?: string
sessionId: string
            }
export type TDataApiAgentContextPost = {
                formData?: Body__api_agent_context_post
sessionId: string
            }
export type TDataApiAgentContextPut = {
                formData?: Body__api_agent_context_put
sessionId: string
            }
export type TDataApiAgentContextDelete = {
                fileId?: string
sessionId: string
            }
export type TDataApiAgentChatGet = {
                sessionId: string
            }
export type TDataApiAgentChatPost = {
                requestBody: ChatRequest
            }
export type TDataApiAgentMessagePost = {
                requestBody: SendMessageRequest
            }
export type TDataApiAgentSessionsPut = {
                sessionId: string
            }
export type TDataApiAgentSessionsDelete = {
                sessionId: string
softDelete?: boolean
            }
export type TDataApiMcpToolsPost = {
                requestBody: ExecuteToolRequest
            }

export class DefaultService {

	/**
	 * Health check endpoint to verify all services
	 * @returns unknown Successful Response
	 * @throws ApiError
	 */
	public static apiHealthGet(): CancelablePromise<unknown> {
				return __request(OpenAPI, {
			method: 'GET',
			url: '/api/health',
		});
	}

	/**
	 * Get agent session information
	 * @returns unknown Successful Response
	 * @throws ApiError
	 */
	public static apiAgentGet(data: TDataApiAgentGet): CancelablePromise<unknown> {
		const {
sessionId,
} = data;
		return __request(OpenAPI, {
			method: 'GET',
			url: '/api/agent',
			query: {
				session_id: sessionId
			},
			errors: {
				422: `Validation Error`,
			},
		});
	}

	/**
	 * Create a new agent session with optional initial context
	 * @returns unknown Successful Response
	 * @throws ApiError
	 */
	public static apiAgentPost(data: TDataApiAgentPost): CancelablePromise<unknown> {
		const {
requestBody,
} = data;
		return __request(OpenAPI, {
			method: 'POST',
			url: '/api/agent',
			body: requestBody,
			mediaType: 'application/json',
			errors: {
				422: `Validation Error`,
			},
		});
	}

	/**
	 * Delete an agent session
	 * @returns unknown Successful Response
	 * @throws ApiError
	 */
	public static apiAgentDelete(data: TDataApiAgentDelete): CancelablePromise<unknown> {
		const {
sessionId,
} = data;
		return __request(OpenAPI, {
			method: 'DELETE',
			url: '/api/agent',
			query: {
				session_id: sessionId
			},
			errors: {
				422: `Validation Error`,
			},
		});
	}

	/**
	 * Get context for a session or a specific file if file_id is provided
	 * @returns unknown Successful Response
	 * @throws ApiError
	 */
	public static apiAgentContextGet(data: TDataApiAgentContextGet): CancelablePromise<unknown> {
		const {
fileId,
sessionId,
} = data;
		return __request(OpenAPI, {
			method: 'GET',
			url: '/api/agent/context',
			query: {
				session_id: sessionId, file_id: fileId
			},
			errors: {
				422: `Validation Error`,
			},
		});
	}

	/**
	 * Append context to a session (adds new context without replacing existing) or upload a new file if file is provided
	 * @returns unknown Successful Response
	 * @throws ApiError
	 */
	public static apiAgentContextPost(data: TDataApiAgentContextPost): CancelablePromise<unknown> {
		const {
formData,
sessionId,
} = data;
		return __request(OpenAPI, {
			method: 'POST',
			url: '/api/agent/context',
			query: {
				session_id: sessionId
			},
			formData: formData,
			mediaType: 'multipart/form-data',
			errors: {
				422: `Validation Error`,
			},
		});
	}

	/**
	 * Update a specific context key for a session or update/replace a file if file is provided
	 * @returns unknown Successful Response
	 * @throws ApiError
	 */
	public static apiAgentContextPut(data: TDataApiAgentContextPut): CancelablePromise<unknown> {
		const {
formData,
sessionId,
} = data;
		return __request(OpenAPI, {
			method: 'PUT',
			url: '/api/agent/context',
			query: {
				session_id: sessionId
			},
			formData: formData,
			mediaType: 'multipart/form-data',
			errors: {
				422: `Validation Error`,
			},
		});
	}

	/**
	 * Remove a specific context key or file from a session
	 * @returns unknown Successful Response
	 * @throws ApiError
	 */
	public static apiAgentContextDelete(data: TDataApiAgentContextDelete): CancelablePromise<unknown> {
		const {
fileId,
sessionId,
} = data;
		return __request(OpenAPI, {
			method: 'DELETE',
			url: '/api/agent/context',
			query: {
				session_id: sessionId, file_id: fileId
			},
			errors: {
				422: `Validation Error`,
			},
		});
	}

	/**
	 * Get chat messages for a session
	 * @returns unknown Successful Response
	 * @throws ApiError
	 */
	public static apiAgentChatGet(data: TDataApiAgentChatGet): CancelablePromise<unknown> {
		const {
sessionId,
} = data;
		return __request(OpenAPI, {
			method: 'GET',
			url: '/api/agent/chat',
			query: {
				session_id: sessionId
			},
			errors: {
				422: `Validation Error`,
			},
		});
	}

	/**
	 * Chat with an agent - creates session if needed, sends message
	 * @returns unknown Successful Response
	 * @throws ApiError
	 */
	public static apiAgentChatPost(data: TDataApiAgentChatPost): CancelablePromise<unknown> {
		const {
requestBody,
} = data;
		return __request(OpenAPI, {
			method: 'POST',
			url: '/api/agent/chat',
			body: requestBody,
			mediaType: 'application/json',
			errors: {
				422: `Validation Error`,
			},
		});
	}

	/**
	 * Send a message to an agent session
	 * @returns unknown Successful Response
	 * @throws ApiError
	 */
	public static apiAgentMessagePost(data: TDataApiAgentMessagePost): CancelablePromise<unknown> {
		const {
requestBody,
} = data;
		return __request(OpenAPI, {
			method: 'POST',
			url: '/api/agent/message',
			body: requestBody,
			mediaType: 'application/json',
			errors: {
				422: `Validation Error`,
			},
		});
	}

	/**
	 * List all active sessions
	 * @returns unknown Successful Response
	 * @throws ApiError
	 */
	public static apiAgentSessionsGet(): CancelablePromise<unknown> {
				return __request(OpenAPI, {
			method: 'GET',
			url: '/api/agent/sessions',
		});
	}

	/**
	 * Update a session (mark active)
	 * @returns unknown Successful Response
	 * @throws ApiError
	 */
	public static apiAgentSessionsPut(data: TDataApiAgentSessionsPut): CancelablePromise<unknown> {
		const {
sessionId,
} = data;
		return __request(OpenAPI, {
			method: 'PUT',
			url: '/api/agent/sessions',
			query: {
				session_id: sessionId
			},
			errors: {
				422: `Validation Error`,
			},
		});
	}

	/**
	 * Delete a session, soft delete by default
	 * @returns unknown Successful Response
	 * @throws ApiError
	 */
	public static apiAgentSessionsDelete(data: TDataApiAgentSessionsDelete): CancelablePromise<unknown> {
		const {
sessionId,
softDelete = true,
} = data;
		return __request(OpenAPI, {
			method: 'DELETE',
			url: '/api/agent/sessions',
			query: {
				session_id: sessionId, soft_delete: softDelete
			},
			errors: {
				422: `Validation Error`,
			},
		});
	}

	/**
	 * List all available tools
	 * @returns unknown Successful Response
	 * @throws ApiError
	 */
	public static apiMcpToolsGet(): CancelablePromise<unknown> {
				return __request(OpenAPI, {
			method: 'GET',
			url: '/api/mcp_tools',
		});
	}

	/**
	 * Execute a tool through the agent
	 * @returns unknown Successful Response
	 * @throws ApiError
	 */
	public static apiMcpToolsPost(data: TDataApiMcpToolsPost): CancelablePromise<unknown> {
		const {
requestBody,
} = data;
		return __request(OpenAPI, {
			method: 'POST',
			url: '/api/mcp_tools',
			body: requestBody,
			mediaType: 'application/json',
			errors: {
				422: `Validation Error`,
			},
		});
	}

	/**
	 * @returns string Successful Response
	 * @throws ApiError
	 */
	public static get(): CancelablePromise<string> {
				return __request(OpenAPI, {
			method: 'GET',
			url: '/',
		});
	}

}