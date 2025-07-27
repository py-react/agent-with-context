export const $ChatRequest = {
	properties: {
		message: {
	type: 'string',
	isRequired: true,
},
		session_id: {
	type: 'any-of',
	contains: [{
	type: 'string',
}, {
	type: 'null',
}],
},
		stream: {
	type: 'any-of',
	contains: [{
	type: 'boolean',
}, {
	type: 'null',
}],
},
	},
} as const;