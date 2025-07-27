export const $ExecuteToolRequest = {
	properties: {
		tool_name: {
	type: 'string',
	isRequired: true,
},
		parameters: {
	type: 'any-of',
	contains: [{
	type: 'dictionary',
	contains: {
	properties: {
	},
},
}, {
	type: 'null',
}],
},
	},
} as const;