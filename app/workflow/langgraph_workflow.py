import time
import uuid
import asyncio
import concurrent.futures
from typing import Dict, Any, List, Optional, AsyncGenerator
from langchain_core.messages import SystemMessage, HumanMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.agents import AgentExecutor, create_openai_tools_agent
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langgraph.graph import StateGraph, END

from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field
from render_relay.utils.get_logger import get_logger
from ..config.config import config
from ..db import WorkflowState, WorkflowStep
from ..db import Message
from datetime import datetime
# Import LLMFactory at runtime to avoid circular imports
# from ..factory.llm_factory import LLMFactory

logger = get_logger("langgraph_workflow")

class IntentAnalysis(BaseModel):
    """Pydantic model for intent analysis output"""
    primary_intent: str = Field(description="The primary intent of the user message")
    secondary_intents: List[str] = Field(default_factory=list, description="Additional intents identified in the message")
    confidence: float = Field(description="Confidence score between 0.0 and 1.0")
    requires_context: bool = Field(description="Whether context lookup is needed")
    tool_requirements: List[str] = Field(default_factory=list, description="List of tool names that might be needed")
    reasoning: str = Field(default="", description="Reasoning for the intent analysis")

class LangGraphWorkflowService:
    """Service for managing LangGraph workflows"""

    def __init__(self, tools: List[BaseTool] = None):
        
        # Import LLMFactory at runtime to avoid circular imports
        from ..factory.llm_factory import LLMFactory
        self.llm = LLMFactory.get_default_llm()
        if not self.llm:
            raise ValueError("No LLM provider configured. Please set up GEMINI_API_KEY or other LLM configuration.")

        # Create structured output LLM for intent analysis
        self.intent_llm = self.llm.with_structured_output(IntentAnalysis)

        self.tools = tools or []

        # Remove parameter models - we'll use tool schemas directly

    def set_tools(self, tools: List[BaseTool]):
        """Set tools for the workflow (dependency injection)"""
        self.tools = tools
        # Recreate parameter extraction agent with new tools
        # This method is no longer needed as parameter extraction is handled by tool schemas

    def _create_workflow(self) -> StateGraph:
        """Create the LangGraph workflow with specific tools"""

        # Create the state graph
        workflow = StateGraph(WorkflowState)

        # Add nodes for each step
        workflow.add_node("intent_analysis", self._analyze_intent)
        workflow.add_node("tool_selection", self._select_tools)
        workflow.add_node("tool_execution", self._execute_tools)
        workflow.add_node("reasoning", self._reason_about_completeness)
        workflow.add_node("response_generation", self._generate_response)

        # Define the workflow flow
        workflow.set_entry_point("intent_analysis")

        # Add edges with conditional routing
        workflow.add_edge("intent_analysis", "tool_selection")
        workflow.add_edge("tool_selection", "tool_execution")
        workflow.add_edge("tool_execution", "reasoning")
        
        # Conditional edge from reasoning to either more tools or response generation
        workflow.add_conditional_edges(
            "reasoning",
            self._should_continue_tool_execution,
            {
                "continue_tools": "tool_execution",
                "generate_response": "response_generation"
            }
        )
        
        workflow.add_edge("response_generation", END)

        # Compile the workflow without checkpointer to avoid database connection issues
        return workflow.compile()

    async def _analyze_intent(self, state: WorkflowState) -> WorkflowState:
        """Analyze user intent dynamically based on available tools"""
        step_start = time.time()
        logger.debug(f"🔍 Starting intent analysis for message: '{state.user_message[:50]}...'")

        step_id = str(uuid.uuid4())
        step = WorkflowStep(
            step_id=step_id,
            step_type="intent_analysis",
            status="running",
            started_at=state.updated_at
        )
        state.add_step(step)
        state.current_step = step_id
        state.workflow_status = "intent_analysis"

        try:
            # Create dynamic system prompt using tool descriptions and conversation history
            system_prompt = self._create_intent_analysis_prompt(state.user_message, state.conversation_history)
            
            logger.debug(f"📋 System prompt length: {len(system_prompt)}")
            logger.debug(f"📋 User message: '{state.user_message}'")
            logger.debug(f"📋 Conversation history length: {len(state.conversation_history) if state.conversation_history else 0}")

            # Get intent analysis from LLM
            messages = [
                SystemMessage(content=system_prompt),
                HumanMessage(content=state.user_message)
            ]

            # Call LLM for structured intent analysis
            intent_result = await self.intent_llm.ainvoke(messages)
            logger.debug(f"✅ LLM intent analysis completed successfully")
            logger.debug(f"📝 Intent result: {intent_result}")

            # Set state from structured output
            state.intent = intent_result.primary_intent
            state.secondary_intents = intent_result.secondary_intents
            state.confidence = intent_result.confidence
            state.requires_context = intent_result.requires_context
            state.tool_requirements = intent_result.tool_requirements
            state.reasoning = intent_result.reasoning

            step.status = "completed"
            step.output_data = {
                "intent": state.intent,
                "confidence": state.confidence,
                "requires_context": state.requires_context,
                "tool_requirements": state.tool_requirements,
                "reasoning": state.reasoning
            }

            step_time = time.time() - step_start
            logger.debug(f"✅ Intent analysis completed in {step_time:.3f}s")

        except Exception as e:
            step.status = "error"
            step.error = str(e)
            state.intent = "general_query"
            state.confidence = 0.5
            state.requires_context = False
            state.tool_requirements = []
            state.reasoning = ""

        return state

    def _generate_tool_intent_mapping(self) -> Dict[str, str]:
        """Generate dynamic intent mapping from available tools"""
        # Remove all hardcoded intents - let tools define their own intents through descriptions
        return {}

    def _create_intent_analysis_prompt(self, user_message: str, conversation_history: List[Message] = None) -> str:
        """Create dynamic system prompt for intent analysis using tool descriptions and conversation history"""
        
        # Build comprehensive tool information
        tool_info = []
        for tool in self.tools:
            tool_info.append(f"""
Tool: {tool.name}
Description: {tool.description}
Parameters: {tool.args_schema.schema() if hasattr(tool, 'args_schema') else 'No parameters'}
""")
        
        tools_text = "\n".join(tool_info)
        
        # Build conversation history context
        conversation_context = ""
        if conversation_history and len(conversation_history) > 1:  # More than just current message
            conversation_context = "\n\nCONVERSATION HISTORY (for context):\n"
            # Include up to config.DEFAULT_MESSAGE_LIMIT messages for context (excluding current message)
            recent_messages = conversation_history[:-1][-config.DEFAULT_MESSAGE_LIMIT:]  # Last messages before current
            for i, msg in enumerate(recent_messages, 1):
                role = msg.role
                content = msg.content[:200] + "..." if len(msg.content) > 200 else msg.content
                conversation_context += f"{i}. {role}: {content}\n"
        
        prompt = f"""You are an intelligent intent analysis expert. Analyze the user's message and determine which tools might be needed to fully address their request.

Available tools:
{tools_text}

{conversation_context}

Current user message: "{user_message}"

Analyze the user's intent and provide:
1. Primary intent (describe the main intent in natural language)
2. Secondary intents (additional intents if the message contains multiple requests or related needs)
3. Confidence score (0.0 to 1.0)
4. Whether context lookup is needed
5. List of tool names that might be needed (based on tool descriptions above)
6. Reasoning for your analysis

CRITICAL REQUIREMENTS:

1. **CONVERSATION HISTORY IS PROVIDED**: 
   - The conversation history is already provided above - use it to understand context
   - Look through the conversation history to find relevant information
   - If the user asks about something mentioned before, check the conversation history first

2. **Multi-Tool Detection**: A single request often requires multiple tools:
   - "What did I tell you about my name?" → Check conversation history + potentially context tools
   - "What's the weather and what time is it?" → Check conversation history (for location) + weather + datetime
   - "Show me the files I uploaded and what we discussed about them" → Check conversation history (for discussions) + context tools (for files)
   - "What did I say about my trip and what's the weather there?" → Check conversation history (to find location) + weather

3. **Context Awareness**: Consider what information might be needed:
   - Personal information shared in conversation → Check conversation history first
   - Files or documents mentioned → Check conversation history (for discussions) + context/document tools
   - Previous discussions or preferences → Check conversation history first
   - System information or calculations → utility tools + conversation history (for context)

4. **Implicit Requirements**: Users often don't explicitly state all their needs:
   - "What did I tell you about my name?" → Check conversation history for name mentions
   - "What files did I upload?" → Check conversation history (for discussions about files) + context retrieval
   - "What's the weather like?" → Check conversation history (for location) + weather

5. **Tool Combinations**: Common intelligent combinations:
   - Personal info queries → Check conversation history + context tools (if files mentioned)
   - File-related queries → Check conversation history (for discussions about files) + context tools (for actual files)
   - Location-based queries → Check conversation history (to find location) + weather/time
   - Multi-part requests → Check conversation history + all relevant tools for each part

6. **Conservative but Comprehensive**: 
   - If unsure about a tool, include it - better to have more information
   - For general conversation or questions about the AI itself, use NO tools
   - For user-specific information, check conversation history first

7. **CONVERSATION HISTORY ANALYSIS**:
   - If user asks about something mentioned before, check the conversation history (already provided above)
   - If user asks "What did I tell you about..." or "What did I say...", check conversation history (already provided above)
   - If user asks about personal information they shared, check conversation history (already provided above)
   - If user asks about previous discussions, check conversation history (already provided above)
   - If user refers to something from earlier in the conversation, check conversation history (already provided above)
   - If user asks "What name did I give you?" or similar questions, check conversation history (already provided above)

Return structured analysis with the specified fields."""
        logger.debug(f"🔍 Intent analysis prompt: {prompt}")
        return prompt

    async def _select_tools(self, state: WorkflowState) -> WorkflowState:
        """Select tools based on intelligent intent analysis"""
        step_start = time.time()
        logger.debug(f"🔧 Starting intelligent tool selection for intent: {state.intent}")

        step_id = str(uuid.uuid4())
        step = WorkflowStep(
            step_id=step_id,
            step_type="tool_selection",
            status="running",
            started_at=state.updated_at
        )
        state.add_step(step)
        state.current_step = step_id
        state.workflow_status = "tool_selection"

        try:
            selected_tools = []
            available_tool_names = [tool.name for tool in self.tools]
            
            # Primary tool selection based on LLM analysis
            logger.debug(f"🔍 Analyzing tool requirements from LLM:")
            logger.debug(f"  - Primary intent: {state.intent}")
            logger.debug(f"  - Secondary intents: {state.secondary_intents}")
            logger.debug(f"  - Tool requirements (LLM): {state.tool_requirements}")
            logger.debug(f"  - Requires context: {state.requires_context}")
            logger.debug(f"  - Reasoning: {state.reasoning}")
            
            # Use LLM's tool recommendations as primary source
            for tool_name in state.tool_requirements:
                if tool_name in available_tool_names:
                    if tool_name not in selected_tools:
                        selected_tools.append(tool_name)
                        logger.debug(f"  ✅ Added tool: {tool_name}")
                else:
                    logger.warning(f"  ⚠️ Tool '{tool_name}' requested by LLM but not found in available tools")
            
            # Intelligent tool combination logic (non-hardcoded)
            if selected_tools:
                # Check if we need additional tools based on the nature of the request
                additional_tools = self._suggest_additional_tools(state, selected_tools, available_tool_names)
                for tool_name in additional_tools:
                    if tool_name not in selected_tools:
                        selected_tools.append(tool_name)
                        logger.debug(f"  🔍 Intelligently added tool: {tool_name}")
            
            # Log final tool selection
            logger.debug(f"🔍 Final tool selection:")
            logger.debug(f"  - Selected tools: {selected_tools}")
            logger.debug(f"  - Multi-tool request: {len(selected_tools) > 1}")
            logger.debug(f"  - Tool selection reasoning: {state.reasoning}")
            logger.debug(f"  - Iteration count: {state.iteration_count}")
            logger.debug(f"  - Previous tool selections: {state.previous_tool_selections}")
            
            if not selected_tools:
                logger.debug(f"  - No tools selected - appropriate for general conversation")
            
            # Store current tool selection for loop detection (only if we have tools and this is a new iteration)
            if selected_tools and len(state.previous_tool_selections) < state.iteration_count:
                state.previous_tool_selections.append(selected_tools.copy())
                logger.debug(f"  - Stored tool selection for iteration {state.iteration_count}")
            
            state.selected_tools = selected_tools

            step.status = "completed"
            step.output_data = {
                "selected_tools": selected_tools,
                "intents_analyzed": [state.intent] + (state.secondary_intents if hasattr(state, 'secondary_intents') else []),
                "multi_tool_selection": len(selected_tools) > 1,
                "tool_requirements": state.tool_requirements,
                "reasoning": state.reasoning,
                "intelligent_selection": True
            }

            step_time = time.time() - step_start
            logger.debug(f"✅ Intelligent tool selection completed in {step_time:.3f}s - selected: {selected_tools}")

        except Exception as e:
            step.status = "error"
            step.error = str(e)
            state.selected_tools = []

        return state

    def _suggest_additional_tools(self, state: WorkflowState, current_tools: List[str], available_tools: List[str]) -> List[str]:
        """Intelligently suggest additional tools based on current selection and user intent"""
        additional_tools = []
        
        # Get tool descriptions for analysis
        tool_descriptions = {}
        for tool in self.tools:
            tool_descriptions[tool.name] = tool.description.lower()
        
        # Analyze current tools and suggest complementary ones
        for tool_name in current_tools:
            description = tool_descriptions.get(tool_name, "")
            
            # If we're looking at context/files, consider if we might need additional context tools
            if any(word in description for word in ["context", "file", "document"]):
                # Check if user might be asking about discussions or what they said
                if any(word in state.user_message.lower() for word in ["discuss", "tell", "said", "mention", "talk"]):
                    context_tools = [t for t in available_tools if any(word in tool_descriptions.get(t, "") for word in ["context", "file", "document"])]
                    additional_tools.extend(context_tools)
            
            # If we're getting weather/time, consider if we might need location from conversation
            elif any(word in description for word in ["weather", "time", "datetime"]):
                # Check if user might need location from conversation history
                if any(word in state.user_message.lower() for word in ["there", "place", "city", "location", "where"]):
                    # The location should be found in the conversation history that's already available
                    pass
        
        # Remove duplicates and already selected tools
        additional_tools = list(set(additional_tools) - set(current_tools))
        
        return additional_tools

    async def _extract_tool_parameters(self, tool_name: str, user_message: str, session_id: str = None, conversation_history: List[Message] = None) -> Dict[str, Any]:
        """Extract parameters for tool execution using intelligent LLM analysis"""
        try:
            # Find the actual tool
            tool = next((t for t in self.tools if t.name == tool_name), None)
            if not tool:
                logger.error(f"❌ Tool {tool_name} not found in available tools")
                return {}

            # Use tool's schema directly if available
            if hasattr(tool, 'args_schema'):
                schema = tool.args_schema.schema()
                logger.debug(f"🔍 Using tool schema for {tool_name}: {schema}")
            else:
                logger.warning(f"⚠️ No schema found for tool {tool_name}, returning empty parameters")
                return {}

            # Build conversation history context for parameter extraction
            conversation_context = ""
            if conversation_history and len(conversation_history) > 1:
                conversation_context = "\n\nCONVERSATION HISTORY (for context):\n"
                recent_messages = conversation_history[:-1][-config.DEFAULT_MESSAGE_LIMIT:]  # Last messages before current
                for i, msg in enumerate(recent_messages, 1):
                    role = msg.role
                    content = msg.content[:100] + "..." if len(msg.content) > 100 else msg.content
                    conversation_context += f"{i}. {role}: {content}\n"

            # Create intelligent parameter extraction prompt
            extraction_prompt = f"""Extract parameters for the {tool_name} tool based on the user message.

Tool: {tool_name}
Description: {tool.description}
Schema: {schema}
User Message: "{user_message}"
Session ID: {session_id or "SESSION_ID"}
{conversation_context}

PARAMETER EXTRACTION GUIDELINES:

1. **Context-Aware Extraction**: Consider what the user is actually asking for:
   - For conversation history tools: Extract meaningful search queries from the user's intent
   - For context tools: Extract relevant search terms for files/documents
   - For utility tools: Extract specific parameters (location, expression, etc.)

2. **Conversation History Context**: 
   - If conversation history is provided, use it to understand context
   - Extract location, names, or other details mentioned in previous messages
   - Use the conversation history to provide better parameter values

3. **Query Optimization**: 
   - For search queries, use key terms that would find relevant information
   - Avoid overly broad queries like "user information" - be more specific
   - Use the user's own words when possible

4. **Session Context**: Always use the provided session_id for tools that need it

5. **Smart Defaults**: Use sensible defaults when parameters aren't specified

6. **Parameter Validation**: Ensure all required parameters are provided and within reasonable limits

EXAMPLES:
- User: "What did I tell you about my name?" → query: "name" or "my name"
- User: "What files did I upload?" → query: "files" or "uploaded documents"
- User: "What's the weather like?" → location: extract from conversation history or use "current"
- User: "Calculate 2+2" → expression: "2+2"

Extract the appropriate parameters and return them as a JSON object that matches the schema.
If a parameter is not mentioned in the user message, use sensible defaults.

Return only the JSON object with the parameters."""

            # Use the LLM to extract parameters
            messages = [
                SystemMessage(content="You are an intelligent parameter extraction expert. Extract tool parameters from user messages with context awareness."),
                HumanMessage(content=extraction_prompt)
            ]
            
            response = await self.llm.ainvoke(messages)
            
            # Parse the response to extract JSON
            import json
            import re
            
            json_match = re.search(r'\{.*\}', response.content, re.DOTALL)
            if json_match:
                params = json.loads(json_match.group())
            else:
                logger.warning(f"⚠️ Could not parse JSON from response for {tool_name}")
                return {}
            
            # Ensure session_id is set for tools that need it
            if session_id and "session_id" in params:
                if params["session_id"] == "SESSION_ID" or not params["session_id"]:
                    params["session_id"] = session_id
            
            # Validate and sanitize parameters
            params = self._validate_parameters(tool_name, params)
            
            logger.debug(f"✅ Extracted parameters for {tool_name}: {params}")
            return params

        except Exception as e:
            logger.error(f"❌ Parameter extraction failed for {tool_name}: {e}")
            return {}

    def _validate_parameters(self, tool_name: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Validate and sanitize tool parameters"""
        try:
            # Ensure reasonable limits for search/query tools
            if "limit" in params:
                if params["limit"] > config.TOOL_MAX_LIMIT:
                    params["limit"] = config.TOOL_DEFAULT_LIMIT
                    logger.debug(f"Adjusted limit for {tool_name} to {config.TOOL_DEFAULT_LIMIT}")
            
            # Ensure session_id is properly set for tools that need it
            if "session_id" in params:
                if not params["session_id"] or params["session_id"] == "SESSION_ID":
                    logger.warning(f"⚠️ Invalid session_id for {tool_name}: {params['session_id']}")
            
            return params
            
        except Exception as e:
            logger.error(f"❌ Parameter validation failed for {tool_name}: {e}")
            return params

    async def _execute_tools(self, state: WorkflowState) -> WorkflowState:
        """Execute selected tools"""
        step_start = time.time()
        logger.debug(f"🔧 Starting tool execution for {len(state.selected_tools)} tools: {state.selected_tools}")

        step_id = str(uuid.uuid4())
        step = WorkflowStep(
            step_id=step_id,
            step_type="tool_execution",
            status="running",
            started_at=state.updated_at
        )
        state.add_step(step)
        state.current_step = step_id
        state.workflow_status = "tool_execution"
        
        # Increment iteration count for loop prevention
        state.iteration_count += 1
        logger.debug(f"🔄 Tool execution iteration {state.iteration_count}/{state.max_iterations}")

        try:
            tool_results = []

            # If no tools are selected, skip execution
            if not state.selected_tools:
                logger.debug("⚠️ No tools selected for execution")
                step.status = "completed"
                step.output_data = {
                    "executed_tools": 0,
                    "successful_tools": 0,
                    "message": "No tools selected for execution"
                }
                step_time = time.time() - step_start
                logger.debug(f"✅ Tool execution completed in {step_time:.3f}s (no tools)")
                return state

            for tool_name in state.selected_tools:
                try:
                    logger.debug(f"🔧 Executing tool: {tool_name}")
                    # Find the actual tool object
                    tool = next((t for t in self.tools if t.name == tool_name), None)
                    if not tool:
                        logger.error(f"❌ Tool {tool_name} not found in available tools: {[t.name for t in self.tools]}")
                        tool_results.append({
                            "tool": tool_name,
                            "result": None,
                            "status": "error",
                            "error": f"Tool {tool_name} not found"
                        })
                        continue

                    # Extract parameters using LangChain agent
                    logger.debug(f"🔍 Extracting parameters for {tool_name}...")
                    params = await self._extract_tool_parameters(tool_name, state.user_message, state.session_id, state.conversation_history)

                    logger.debug(f"✅ Extracted parameters for {tool_name}: {params}")

                    # Execute the tool with extracted parameters
                    try:
                        if hasattr(tool, 'ainvoke'):
                            result = await tool.ainvoke(params)
                        else:
                            # Run synchronous tools in a thread pool to avoid event loop issues
                            with concurrent.futures.ThreadPoolExecutor() as executor:
                                future = executor.submit(tool.invoke, params)
                                result = future.result(timeout=30.0)
                    except Exception as tool_error:
                        logger.error(f"❌ Tool execution failed for {tool_name}: {tool_error}")
                        raise tool_error

                    logger.debug(f"✅ Tool {tool_name} executed successfully")
                    tool_results.append({
                        "tool": tool_name,
                        "result": result,
                        "status": "success",
                        "parameters": params
                    })

                except Exception as e:
                    logger.error(f"❌ Tool {tool_name} execution failed: {e}")
                    tool_results.append({
                        "tool": tool_name,
                        "result": None,
                        "status": "error",
                        "error": str(e)
                    })

            state.tool_results = tool_results

            step.status = "completed"
            step.output_data = {
                "executed_tools": len(state.selected_tools),
                "successful_tools": len([r for r in tool_results if r["status"] == "success"]),
                "tool_results": tool_results
            }

            step_time = time.time() - step_start
            logger.debug(f"✅ Tool execution completed in {step_time:.3f}s")

        except Exception as e:
            step.status = "error"
            step.error = str(e)
            state.tool_results = []

        return state

    async def _reason_about_completeness(self, state: WorkflowState) -> WorkflowState:
        """Reason about the completeness of the tool execution and determine if more tools are needed."""
        step_start = time.time()
        logger.debug(f"🧠 Starting reasoning about tool execution completeness for intent: {state.intent}")

        step_id = str(uuid.uuid4())
        step = WorkflowStep(
            step_id=step_id,
            step_type="reasoning",
            status="running",
            started_at=state.updated_at
        )
        state.add_step(step)
        state.current_step = step_id
        state.workflow_status = "reasoning"

        try:
            # Combine tool results and user message for reasoning
            tool_results_text = ""
            if state.tool_results:
                tool_results_text = "Tool Results:\n"
                for i, result in enumerate(state.tool_results, 1):
                    tool_name = result.get("tool", f"Tool {i}")
                    tool_result = result.get("result", "No result")
                    status = result.get("status", "unknown")
                    tool_results_text += f"{tool_name} ({status}): {tool_result}\n"
            
            # Build conversation history context for reasoning
            conversation_context = ""
            if state.conversation_history and len(state.conversation_history) > 1:
                conversation_context = "\n\nCONVERSATION HISTORY (for context):\n"
                recent_messages = state.conversation_history[:-1][-config.DEFAULT_MESSAGE_LIMIT:]  # Last messages before current
                for i, msg in enumerate(recent_messages, 1):
                    role = msg.role
                    content = msg.content[:100] + "..." if len(msg.content) > 100 else msg.content
                    conversation_context += f"{i}. {role}: {content}\n"
            
            # Combine tool results with user message for LLM reasoning
            reasoning_prompt = f"""You are an intelligent reasoning expert. Analyze the user's message and the results of the tools executed.

User Message: "{state.user_message}"

{conversation_context}

Tool Results:
{tool_results_text}

Primary Intent: {state.intent}
Secondary Intents: {state.secondary_intents if state.secondary_intents else 'None'}
Reasoning: {state.reasoning}

Iteration Information:
- Current iteration: {state.iteration_count}
- Maximum iterations: {state.max_iterations}
- Previous tool selections: {state.previous_tool_selections}

INTELLIGENT REASONING GUIDELINES:

1. **Determine if More Tools are Needed**:
   - If the user's request is fully addressed by the current tool results, return "generate_response".
   - If the user's request is not fully addressed, return "continue_tools".
   - If the user's request is ambiguous or requires further clarification, return "continue_tools".

2. **Conversation History Queries**:
   - If the user asks about something mentioned in conversation history (names, preferences, etc.), return "generate_response".
   - The conversation history is already provided above and contains the necessary context to answer the user's question.
   - Do NOT continue tool execution for conversation history queries.

3. **Consider Context**:
   - If the user's message implies a need for more information or a different tool, return "continue_tools".
   - If the user's message is a follow-up to a previous tool's result, return "continue_tools".
   - If the user's message is a general question about the AI itself, return "generate_response".
   - If conversation history provides relevant information, consider it in your reasoning.

4. **Tool Limitations**:
   - If a tool found no relevant information, mention this in the reasoning.
   - If a tool's result is incomplete, mention this in the reasoning.
   - If a tool's result is contradictory, mention this in the reasoning.

5. **Natural Language Reasoning**:
   - Use the user's own words when possible.
   - Be concise and clear.
   - Avoid repeating the same information.
   - Reference conversation history when relevant.

EXAMPLES:
- If user asks "What name did I give you?" and conversation history is provided: "The conversation history is already provided above and contains the information needed to answer the user's question about the name they gave me. Proceed to generate response."
- If conversation history + context tools were used and provided relevant info: "Based on our conversation and the files, I have answered your question. If you need more details or a different tool, let me know."
- If weather + conversation history: "You mentioned you're going to [location from conversation]. The weather there is [weather info]. If you need more details or a different tool, let me know."
- If multiple tools found nothing: "I checked our conversation history and uploaded files, but I couldn't find specific information about [topic]. If you need more details or a different tool, let me know."
- If user asks a general question: "I'm an AI assistant. I can help answer questions about my capabilities. If you need more specific information, let me know."

Provide a clear, concise, and intelligent reasoning that determines whether to continue tool execution or generate a response.

Reasoning:"""

            # Get reasoning from LLM
            messages = [
                SystemMessage(content="You are an intelligent reasoning expert. Analyze the user's message and the results of the tools executed."),
                HumanMessage(content=reasoning_prompt)
            ]
            
            response_result = await self.llm.ainvoke(messages)
            reasoning_output = response_result.content

            # Determine next step based on reasoning
            if "generate_response" in reasoning_output.lower():
                logger.debug(f"✅ LLM determined to generate response.")
                state.workflow_status = "response_generation"
                step.status = "completed"
                step.output_data = {
                    "reasoning": reasoning_output,
                    "next_step": "response_generation"
                }
            elif "continue_tools" in reasoning_output.lower():
                logger.debug(f"✅ LLM determined to continue tool execution.")
                state.workflow_status = "tool_execution"
                step.status = "completed"
                step.output_data = {
                    "reasoning": reasoning_output,
                    "next_step": "tool_execution"
                }
            else:
                logger.warning(f"⚠️ LLM reasoning output not recognized: {reasoning_output}")
                state.workflow_status = "tool_execution"
                step.status = "completed"
                step.output_data = {
                    "reasoning": reasoning_output,
                    "next_step": "tool_execution"
                }

            step_time = time.time() - step_start
            logger.debug(f"✅ Reasoning completed in {step_time:.3f}s")

        except Exception as e:
            step.status = "error"
            step.error = str(e)
            state.workflow_status = "tool_execution" # Ensure we don't get stuck in reasoning
            state.reasoning = "" # Clear previous reasoning

        return state

    def _should_continue_tool_execution(self, state: WorkflowState) -> str:
        """Determine if tool execution should continue based on the reasoning output and loop prevention."""
        
        # Check iteration limits to prevent infinite loops
        if state.iteration_count >= state.max_iterations:
            logger.warning(f"⚠️ Maximum iterations ({state.max_iterations}) reached, forcing response generation")
            return "generate_response"
        
        # Check for repeated tool selections (loop detection)
        if state.selected_tools and state.previous_tool_selections:
            current_tools = sorted(state.selected_tools)
            logger.debug(f"🔍 Checking for repeated tool selection:")
            logger.debug(f"  - Current tools: {current_tools}")
            logger.debug(f"  - Previous selections: {state.previous_tool_selections}")
            
            for i, previous_tools in enumerate(state.previous_tool_selections):
                if sorted(previous_tools) == current_tools:
                    logger.warning(f"⚠️ Detected repeated tool selection at index {i}: {current_tools}, forcing response generation")
                    return "generate_response"
        
        # Special handling for conversation history queries
        # If user is asking about conversation history and no tools are selected, proceed to response generation
        if any(word in state.user_message.lower() for word in ["name", "tell", "said", "mention", "discuss", "talk"]) and not state.selected_tools:
            logger.debug(f"✅ User asking about conversation history, conversation history already provided, proceeding to response generation")
            return "generate_response"
        
        # Check reasoning output
        reasoning_output = state.reasoning.lower()
        if "generate_response" in reasoning_output:
            return "generate_response"
        elif "continue_tools" in reasoning_output:
            return "continue_tools"
        else:
            # Default to continue if reasoning is not clear
            return "continue_tools"

    async def _generate_response(self, state: WorkflowState) -> WorkflowState:
        """Generate final response based on tool results and intent"""
        step_start = time.time()
        logger.debug(f"💬 Starting response generation for intent: {state.intent}")

        step_id = str(uuid.uuid4())
        step = WorkflowStep(
            step_id=step_id,
            step_type="response_generation",
            status="running",
            started_at=state.updated_at
        )
        state.add_step(step)
        state.current_step = step_id
        state.workflow_status = "response_generation"

        try:
            # Prepare context for response generation
            context_parts = []
            
            # Add tool results to context
            if state.tool_results:
                context_parts.append("Tool Results:")
                for i, result in enumerate(state.tool_results, 1):
                    tool_name = result.get("tool", f"Tool {i}")
                    tool_result = result.get("result", "No result")
                    status = result.get("status", "unknown")
                    context_parts.append(f"{tool_name} ({status}): {tool_result}")
            
            # Add conversation history context
            if state.conversation_history and len(state.conversation_history) > 1:  # More than just current message
                context_parts.append("Conversation History:")
                # Include up to config.DEFAULT_MESSAGE_LIMIT messages for context (excluding current message)
                recent_messages = state.conversation_history[:-1][-config.DEFAULT_MESSAGE_LIMIT:]  # Last messages before current
                for i, msg in enumerate(recent_messages, 1):
                    role = msg.role
                    content = msg.content[:150] + "..." if len(msg.content) > 150 else msg.content
                    context_parts.append(f"{i}. {role}: {content}")
            
            context = "\n".join(context_parts) if context_parts else "No additional context available."
            
            # Create response generation prompt
            if len(state.selected_tools) > 1:
                # Multi-tool response - intelligent synthesis
                prompt = f"""You are a helpful AI assistant. The user asked: "{state.user_message}"

Multiple tools were used to gather comprehensive information:
{context}

Primary Intent: {state.intent}
Secondary Intents: {state.secondary_intents if state.secondary_intents else 'None'}
Reasoning: {state.reasoning}

INTELLIGENT RESPONSE GUIDELINES:

1. **Check Conversation History First**: If the user asks about something mentioned before, look through the conversation history to find the answer.

2. **Synthesize Information**: Combine information from all tools and conversation history in a natural, conversational way

3. **Address All Aspects**: Make sure to address every part of the user's request

4. **Context Integration**: If conversation history provides context that helps explain tool results, connect them

5. **Missing Information**: If some tools found no relevant information, mention this honestly

6. **Natural Flow**: Present information in a logical, easy-to-follow manner

EXAMPLES:
- If user asks about names: "Based on our conversation, you told me to call you [name from conversation history]."
- If conversation history + context tools were used: "Based on our conversation, you mentioned [conversation info]. Regarding the files you uploaded, [file info]."
- If weather + conversation history: "You mentioned you're going to [location from conversation]. The weather there is [weather info]."
- If multiple tools found nothing: "I checked our conversation history and uploaded files, but I couldn't find specific information about [topic]."

Provide a comprehensive, intelligent response that addresses all aspects of the user's request.

Response:"""
            else:
                # Single tool response - focused and direct
                prompt = f"""You are a helpful AI assistant. The user asked: "{state.user_message}"

Information gathered:
{context}

Intent: {state.intent}
Reasoning: {state.reasoning}

RESPONSE GUIDELINES:

1. **Check Conversation History First**: If the user asks about something mentioned before, look through the conversation history to find the answer.

2. **Use Context Appropriately**: 
   - If the user asks "What name did I give you?" or similar questions, check the conversation history for where they mentioned names or nicknames
   - If the user asks about previous discussions, check the conversation history for relevant information
   - If the user asks about personal information they shared, check the conversation history first

3. **Be Accurate**: If you find relevant information in the conversation history, use it. If you don't find relevant information, be honest about it.

4. **Natural Responses**: Provide natural, conversational responses that directly answer the user's question.

EXAMPLES:
- User: "What name did I give you?" → Check conversation history for name mentions and respond with what they said
- User: "What did I tell you about my trip?" → Check conversation history for trip-related discussions
- User: "What did we talk about before?" → Summarize relevant parts of the conversation history

Provide a helpful, direct response based on the gathered information and conversation history.
If no relevant information was found, be honest about it and ask for clarification if needed.

Response:"""

            # Generate response using LLM
            messages = [
                SystemMessage(content="You are a helpful AI assistant that provides clear, accurate, and helpful responses."),
                HumanMessage(content=prompt)
            ]
            
            response_result = await self.llm.ainvoke(messages)
            response = response_result.content

            state.response = response
            state.final_response = response

            step.status = "completed"
            step.output_data = {
                "response": response,
                "response_length": len(response),
                "tools_used": len(state.selected_tools),
                "multi_tool_response": len(state.selected_tools) > 1
            }

            step_time = time.time() - step_start
            logger.debug(f"✅ Response generation completed in {step_time:.3f}s - response length: {len(response)}")

        except Exception as e:
            step.status = "error"
            step.error = str(e)
            state.response = f"I apologize, but I encountered an error while generating a response: {str(e)}"
            state.final_response = state.response

        return state

    async def _setup_workflow_state(self, session_id: str, user_message: str, conversation_history: List[Dict[str, Any]] = None) -> WorkflowState:
        """Helper method to set up workflow state with conversation history"""
        setup_start = time.time()
        logger.debug("📋 Setting up workflow state...")

        # Fetch previous messages for context
        previous_messages = []
        if conversation_history:
            # Use provided conversation history
            for msg in conversation_history:
                # Handle timestamp conversion safely
                timestamp_value = msg.get("timestamp")
                if isinstance(timestamp_value, str):
                    timestamp = datetime.fromisoformat(timestamp_value)
                elif isinstance(timestamp_value, datetime):
                    timestamp = timestamp_value
                else:
                    timestamp = datetime.now()
                
                previous_messages.append(Message(
                    role=msg.get("role", "user"),
                    content=msg.get("content", ""),
                    timestamp=timestamp,
                    metadata=msg.get("metadata", {})
                ))
        else:
            # Fetch from message history service
            try:
                from ..factory.service_factory import service_factory
                message_service = service_factory.get_service('message_history')
                messages_result = message_service.get_previous_messages(session_id, source="auto")
                
                import json
                if isinstance(messages_result, str):
                    messages_data = json.loads(messages_result)
                else:
                    messages_data = messages_result
                
                if messages_data.get("status") == "success" and messages_data.get("messages"):
                    for msg_data in messages_data["messages"]:
                        # Handle timestamp conversion safely
                        timestamp_value = msg_data.get("timestamp")
                        if isinstance(timestamp_value, str):
                            timestamp = datetime.fromisoformat(timestamp_value)
                        elif isinstance(timestamp_value, datetime):
                            timestamp = timestamp_value
                        else:
                            timestamp = datetime.now()
                        
                        previous_messages.append(Message(
                            role=msg_data.get("role", "user"),
                            content=msg_data.get("content", ""),
                            timestamp=timestamp,
                            metadata=msg_data.get("metadata", {})
                        ))
                    logger.debug(f"✅ Fetched {len(previous_messages)} previous messages for context")
                else:
                    logger.debug(f"⚠️ No previous messages found or error: {messages_data.get('message', 'Unknown error')}")
            except Exception as e:
                logger.warning(f"⚠️ Failed to fetch previous messages: {e}")

        # Add current message
        current_message = Message(
            role="user",
            content=user_message,
            timestamp=datetime.now(),
            metadata={}
        )
        
        # Combine previous messages with current message
        all_messages = previous_messages + [current_message]
        
        workflow_state = WorkflowState(
            session_id=session_id,
            user_message=user_message,
            conversation_history=all_messages  # Include all messages for context
        )

        # Initialize steps field
        workflow_state.steps = workflow_state.workflow_steps
        setup_time = time.time() - setup_start
        logger.debug(f"✅ Workflow state setup completed in {setup_time:.3f}s")
        
        return workflow_state

    async def process_message(self, session_id: str, user_message: str, conversation_history: List[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Process a message through the LangGraph workflow"""
        start_time = time.time()
        logger.info(f"🚀 LangGraphWorkflow.process_message started - session_id: {session_id}, message_length: {len(user_message)}")

        try:
            # Create workflow state using helper method
            setup_start = time.time()
            workflow_state = await self._setup_workflow_state(session_id, user_message, conversation_history)
            setup_time = time.time() - setup_start

            # Create and run workflow
            workflow_start = time.time()
            logger.debug("🔧 Creating workflow...")
            workflow = self._create_workflow()
            workflow_create_time = time.time() - workflow_start
            logger.debug(f"✅ Workflow created in {workflow_create_time:.3f}s")

            # Invoke workflow without checkpointer configuration
            invoke_start = time.time()
            logger.info("🚀 Invoking workflow...")
            result = await workflow.ainvoke(workflow_state)
            invoke_time = time.time() - invoke_start
            logger.info(f"✅ Workflow invocation completed in {invoke_time:.3f}s")

            # Extract metadata
            metadata_start = time.time()
            logger.debug("📊 Extracting metadata...")
            metadata = {
                "intent": result.get("intent"),
                "confidence": result.get("confidence"),
                "requires_context": result.get("requires_context"),
                "requires_tools": len(result.get("selected_tools", [])) > 0,
                "tool_calls": [
                    {
                        "tool": tool_result["tool"],
                        "result": tool_result["result"],
                        "status": tool_result.get("status", "success"),
                        "error": tool_result.get("error")
                    }
                    for tool_result in result.get("tool_results", [])
                ],
                "session_context_used": result.get("requires_context")
            }
            metadata_time = time.time() - metadata_start
            logger.debug(f"✅ Metadata extraction completed in {metadata_time:.3f}s")

            total_time = time.time() - start_time
            logger.info(f"🎉 LangGraphWorkflow.process_message completed successfully in {total_time:.3f}s (setup: {setup_time:.3f}s, workflow_create: {workflow_create_time:.3f}s, invoke: {invoke_time:.3f}s, metadata: {metadata_time:.3f}s)")

            return {
                "status": "success",
                "response": result.get("response"),
                "metadata": metadata,
                "workflow_state": {
                    "workflow_status": result.get("workflow_status"),
                    "steps": [step.dict() for step in result.get("steps", [])]
                }
            }

        except Exception as e:
            total_time = time.time() - start_time
            logger.error(f"❌ LangGraphWorkflow.process_message failed after {total_time:.3f}s: {str(e)}", exc_info=True)
            return {
                "status": "error",
                "response": f"Workflow processing failed: {str(e)}",
                "error": str(e)
            }

    async def process_message_stream(self, session_id: str, user_message: str, conversation_history: List[Dict[str, Any]] = None) -> AsyncGenerator[Dict[str, Any], None]:
        """Process a message through the LangGraph workflow with streaming updates"""
        start_time = time.time()
        logger.info(f"🚀 LangGraphWorkflow.process_message_stream started - session_id: {session_id}, message_length: {len(user_message)}")

        try:
            # Send initial status
            initial_status = {
                "type": "status",
                "message": "Setting up workflow state...",
                "timestamp": time.time()
            }
            logger.debug(f"🔍 Yielding initial status: {initial_status}")
            yield initial_status

            # Create workflow state using helper method
            workflow_state = await self._setup_workflow_state(session_id, user_message, conversation_history)

            yield {
                "type": "status",
                "message": "Creating workflow...",
                "timestamp": time.time()
            }

            # Create workflow
            workflow_start = time.time()
            logger.debug("🔧 Creating workflow...")
            workflow = self._create_workflow()
            workflow_create_time = time.time() - workflow_start
            logger.debug(f"✅ Workflow created in {workflow_create_time:.3f}s")

            intent_status = {
                "type": "status",
                "message": "Starting intent analysis...",
                "timestamp": time.time()
            }
            logger.debug(f"🔍 Yielding intent status: {intent_status}")
            yield intent_status

            # Execute intent analysis step
            intent_result = await self._analyze_intent(workflow_state)
            step_complete_event = {
                "type": "step_complete",
                "step": "intent_analysis",
                "result": {
                    "intent": intent_result.intent,
                    "confidence": intent_result.confidence,
                    "requires_context": intent_result.requires_context,
                    "tool_requirements": intent_result.tool_requirements
                },
                "timestamp": time.time()
            }
            logger.debug(f"🔍 Yielding intent analysis complete: {step_complete_event}")
            yield step_complete_event

            yield {
                "type": "status",
                "message": "Selecting tools...",
                "timestamp": time.time()
            }

            # Execute tool selection step
            tool_selection_result = await self._select_tools(workflow_state)
            yield {
                "type": "step_complete",
                "step": "tool_selection",
                "result": {
                    "selected_tools": tool_selection_result.selected_tools
                },
                "timestamp": time.time()
            }

            # Execute tool execution step if tools are selected
            if tool_selection_result.selected_tools:
                yield {
                    "type": "status",
                    "message": f"Executing {len(tool_selection_result.selected_tools)} tools...",
                    "timestamp": time.time()
                }

                # Execute tools one by one and stream updates
                tool_results = []
                for tool_name in tool_selection_result.selected_tools:

                    # Find the tool
                    tool = None
                    for t in self.tools:
                        if t.name == tool_name:
                            tool = t
                            break

                    if tool:
                        # Extract parameters using LangChain agent
                        logger.debug(f"🔍 Extracting parameters for {tool_name}...")
                        tool_params = await self._extract_tool_parameters(tool_name, user_message, session_id)

                        logger.debug(f"✅ Extracted parameters for {tool_name}: {tool_params}")

                        # Start tool call
                        yield {
                            "type": "tool_call_start",
                            "tool": tool_name,
                            "input": tool_params,
                            "timestamp": time.time()
                        }

                        try:
                            # Execute tool with extracted parameters
                            if hasattr(tool, 'ainvoke'):
                                result = await tool.ainvoke(tool_params)
                            else:
                                # Run synchronous tools in a thread pool to avoid event loop issues
                                with concurrent.futures.ThreadPoolExecutor() as executor:
                                    future = executor.submit(tool.invoke, tool_params)
                                    result = future.result(timeout=30.0)

                            # Tool completed successfully
                            yield {
                                "type": "tool_call_complete",
                                "tool": tool_name,
                                "output": result,
                                "timestamp": time.time()
                            }

                            tool_results.append({
                                "tool": tool_name,
                                "result": result,
                                "status": "success",
                                "parameters": tool_params
                            })

                        except Exception as e:
                            # Tool failed
                            yield {
                                "type": "tool_call_error",
                                "tool": tool_name,
                                "error": str(e),
                                "timestamp": time.time()
                            }

                            tool_results.append({
                                "tool": tool_name,
                                "result": None,
                                "status": "error",
                                "error": str(e),
                                "parameters": tool_params
                            })

                # Update workflow state with tool results
                workflow_state.tool_results = tool_results

            yield {
                "type": "status",
                "message": "Reasoning about tool execution completeness...",
                "timestamp": time.time()
            }

            # Execute reasoning step
            reasoning_result = await self._reason_about_completeness(workflow_state)
            yield {
                "type": "step_complete",
                "step": "reasoning",
                "result": {
                    "reasoning": reasoning_result.reasoning,
                    "next_step": reasoning_result.workflow_status
                },
                "timestamp": time.time()
            }

            # Conditional routing based on reasoning
            if reasoning_result.workflow_status == "tool_execution":
                # Check loop prevention before continuing
                if workflow_state.iteration_count >= workflow_state.max_iterations:
                    logger.warning(f"⚠️ Maximum iterations ({workflow_state.max_iterations}) reached in streaming, forcing response generation")
                    yield {
                        "type": "status",
                        "message": "Maximum iterations reached, generating response...",
                        "timestamp": time.time()
                    }
                else:
                    # Check for repeated tool selections
                    current_tools = sorted(tool_selection_result.selected_tools)
                    is_repeated = False
                    for previous_tools in workflow_state.previous_tool_selections:
                        if sorted(previous_tools) == current_tools:
                            logger.warning(f"⚠️ Detected repeated tool selection in streaming: {current_tools}, forcing response generation")
                            is_repeated = True
                            break
                    
                    if is_repeated:
                        yield {
                            "type": "status",
                            "message": "Repeated tool selection detected, generating response...",
                            "timestamp": time.time()
                        }
                    else:
                        yield {
                            "type": "status",
                            "message": "Executing more tools...",
                            "timestamp": time.time()
                        }
                        # Re-execute tool selection and execution if more tools are needed
                        tool_selection_result = await self._select_tools(workflow_state)
                        yield {
                            "type": "step_complete",
                            "step": "tool_selection",
                            "result": {
                                "selected_tools": tool_selection_result.selected_tools
                            },
                            "timestamp": time.time()
                        }

                        if tool_selection_result.selected_tools:
                            yield {
                                "type": "status",
                                "message": f"Executing {len(tool_selection_result.selected_tools)} more tools...",
                                "timestamp": time.time()
                            }
                            tool_results = []
                            for tool_name in tool_selection_result.selected_tools:
                                tool = None
                                for t in self.tools:
                                    if t.name == tool_name:
                                        tool = t
                                        break
                                if tool:
                                    logger.debug(f"🔍 Extracting parameters for {tool_name}...")
                                    tool_params = await self._extract_tool_parameters(tool_name, user_message, session_id)
                                    logger.debug(f"✅ Extracted parameters for {tool_name}: {tool_params}")
                                    yield {
                                        "type": "tool_call_start",
                                        "tool": tool_name,
                                        "input": tool_params,
                                        "timestamp": time.time()
                                    }
                                    try:
                                        if hasattr(tool, 'ainvoke'):
                                            result = await tool.ainvoke(tool_params)
                                        else:
                                            with concurrent.futures.ThreadPoolExecutor() as executor:
                                                future = executor.submit(tool.invoke, tool_params)
                                                result = future.result(timeout=30.0)
                                    except Exception as e:
                                        yield {
                                            "type": "tool_call_error",
                                            "tool": tool_name,
                                            "error": str(e),
                                            "timestamp": time.time()
                                        }
                                        tool_results.append({
                                            "tool": tool_name,
                                            "result": None,
                                            "status": "error",
                                            "error": str(e),
                                            "parameters": tool_params
                                        })
                                    else:
                                        yield {
                                            "type": "tool_call_complete",
                                            "tool": tool_name,
                                            "output": result,
                                            "timestamp": time.time()
                                        }
                                        tool_results.append({
                                            "tool": tool_name,
                                            "result": result,
                                            "status": "success",
                                            "parameters": tool_params
                                        })
                            workflow_state.tool_results = tool_results

            yield {
                "type": "status",
                "message": "Generating response...",
                "timestamp": time.time()
            }

            # Execute response generation step
            response_result = await self._generate_response(workflow_state)
            yield {
                "type": "step_complete",
                "step": "response_generation",
                "result": {
                    "response_length": len(response_result.response) if response_result.response else 0
                },
                "timestamp": time.time()
            }

            # Stream the response word by word
            if response_result.response:
                yield {
                    "type": "response_start",
                    "timestamp": time.time()
                }

                words = response_result.response.split()
                for i, word in enumerate(words):
                    yield {
                        "type": "response_chunk",
                        "content": word + " ",
                        "is_complete": i == len(words) - 1,
                        "timestamp": time.time()
                    }
                    await asyncio.sleep(0.05)  # Small delay for streaming effect

                yield {
                    "type": "response_complete",
                    "full_response": response_result.response,
                    "timestamp": time.time()
                }

            total_time = time.time() - start_time
            logger.info(f"🎉 LangGraphWorkflow.process_message_stream completed successfully in {total_time:.3f}s")

        except Exception as e:
            total_time = time.time() - start_time
            logger.error(f"❌ LangGraphWorkflow.process_message_stream failed after {total_time:.3f}s: {str(e)}", exc_info=True)
            yield {
                "type": "error",
                "message": f"Workflow processing failed: {str(e)}",
                "timestamp": time.time()
            } 