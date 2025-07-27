export const $SendMessageRequest = {
	properties: {
		session_id: {
	type: 'string',
	isRequired: true,
},
		message: {
	type: 'string',
	isRequired: true,
},
	},
} as const;