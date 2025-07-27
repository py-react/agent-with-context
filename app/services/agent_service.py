import os
from typing import List, Dict, Any, Optional
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.agents import AgentExecutor, create_openai_tools_agent
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.tools import BaseTool
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langchain_core.callbacks import BaseCallbackHandler
from ..db import MessageRole, AgentState
from ..config.config import config
from ..factory.llm_factory import LLMFactory
# Service factory import removed to avoid circular imports

class ToolCallbackHandler(BaseCallbackHandler):
    """Callback handler to capture tool usage"""
    
    def __init__(self):
        self.tool_calls = []
    
    def on_tool_start(self, serialized, input_str, **kwargs):
        """Called when a tool starts"""
        self.tool_calls.append({
            "tool": serialized.get("name", "unknown"),
            "input": input_str,
            "output": None
        })
    
    def on_tool_end(self, output, **kwargs):
        """Called when a tool ends"""
        if self.tool_calls:
            self.tool_calls[-1]["output"] = output

class AgentService:
    """Service for managing LangChain agents with tools"""
    
    def __init__(self, tools: List[BaseTool] = None):
        
        self.llm = LLMFactory.get_default_llm()
        if not self.llm:
            raise ValueError("No LLM provider configured. Please set up GEMINI_API_KEY or other LLM configuration.")
        
        self.tools = tools or []
        self.agent_executor = None
        if self.tools:
            self.agent_executor = self._create_agent()
    
    def set_tools(self, tools: List[BaseTool]):
        """Set tools for the agent (dependency injection)"""
        self.tools = tools
        self.agent_executor = self._create_agent()
    
    def _create_agent(self) -> AgentExecutor:
        """Create a LangChain agent with tools"""
        
        # System prompt
        system_prompt = """You are a helpful AI assistant powered by Google's Gemini model. 
        You have access to various tools to help answer questions and perform tasks.
        
        Always be helpful, informative, and conversational in your responses."""
        
        # Create the prompt template
        prompt = ChatPromptTemplate.from_messages([
            ("system", system_prompt),
            MessagesPlaceholder(variable_name="chat_history"),
            ("human", "{input}"),
            MessagesPlaceholder(variable_name="agent_scratchpad"),
        ])
        
        # Create the agent
        agent = create_openai_tools_agent(
            llm=self.llm,
            tools=self.tools,
            prompt=prompt
        )
        
        # Create the agent executor
        agent_executor = AgentExecutor(
            agent=agent,
            tools=self.tools,
            verbose=True,
            handle_parsing_errors=True,
            return_intermediate_steps=True
        )
        
        return agent_executor
    
    def _convert_messages_to_langchain(self, messages: List[Dict[str, Any]]) -> List:
        """Convert our message format to LangChain format"""
        langchain_messages = []
        
        for msg in messages:
            if msg["role"] == MessageRole.SYSTEM:
                langchain_messages.append(SystemMessage(content=msg["content"]))
            elif msg["role"] == MessageRole.USER:
                langchain_messages.append(HumanMessage(content=msg["content"]))
            elif msg["role"] == MessageRole.ASSISTANT:
                langchain_messages.append(AIMessage(content=msg["content"]))
        
        return langchain_messages
    
    async def process_message(self, agent_state: AgentState, user_message: str) -> Dict[str, Any]:
        """Process a message using the LangChain agent with tools"""
        if not self.agent_executor:
            return {
                "status": "error",
                "response": "No tools available for agent execution",
                "error": "Tools not configured"
            }
        
        try:
            # Convert existing messages to LangChain format for chat history
            chat_history = self._convert_messages_to_langchain([
                msg.dict() for msg in agent_state.messages
            ])
            
            # Execute the agent
            result = await self.agent_executor.ainvoke({
                "input": user_message,
                "chat_history": chat_history
            })
            
            # Extract tool calls from intermediate steps
            tool_calls = []
            intermediate_steps = result.get("intermediate_steps", [])
            
            for step in intermediate_steps:
                if len(step) >= 2:
                    action = step[0]
                    observation = step[1]
                    
                    tool_calls.append({
                        "tool": action.tool if hasattr(action, 'tool') else str(action),
                        "input": action.tool_input if hasattr(action, 'tool_input') else action,
                        "output": observation
                    })
            
            return {
                "status": "success",
                "response": result["output"],
                "tool_calls": tool_calls,
                "requires_tools": len(tool_calls) > 0
            }
            
        except Exception as e:
            return {
                "status": "error",
                "response": f"I encountered an error: {str(e)}",
                "error": str(e)
            }
    
    def get_available_tools(self) -> List[Dict[str, Any]]:
        """Get information about available tools"""
        return [
            {
                "name": tool.name,
                "description": tool.description,
                "args_schema": tool.args_schema.schema() if hasattr(tool, 'args_schema') else None
            }
            for tool in self.tools
        ] 