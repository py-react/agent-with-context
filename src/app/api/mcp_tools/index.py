from fastapi import Request
from pydantic import BaseModel
from app.factory.tool_factory import ToolFactory
from app.factory.service_factory import service_factory
from typing import Dict, Any, Optional

class ExecuteToolRequest(BaseModel):
    tool_name: str
    parameters: Optional[Dict[str, Any]] = None

async def GET(request: Request):
    """List all available tools"""
    try:
        # Get tools directly from tool factory
        tool_factory = ToolFactory()
        tools = tool_factory.get_tools()
        
        # Convert tools to the expected format
        tools_info = [
            {
                "name": tool.name,
                "description": tool.description,
                "args_schema": tool.args_schema.schema() if hasattr(tool, 'args_schema') else None
            }
            for tool in tools
        ]
        
        return {
            "status": "success",
            "tools": tools_info,
            "count": len(tools_info)
        }
    except Exception as e:
        return {
            "status": "error",
            "message": f"Failed to list tools: {str(e)}"
        }

async def POST(request: Request, execute_request: ExecuteToolRequest):
    """Execute a tool through the agent"""
    try:
        # Get services directly from service factory
        agent_service = service_factory.get_service('agent')
        
        # Get models directly from service factory
        models = service_factory.get_models()
        AgentState = models['AgentState']
        
        # Create a temporary agent state for tool execution
        temp_state = AgentState(session_id="temp")
        
        # Process the message through the agent
        result = await agent_service.process_message(temp_state, f"Use the {execute_request.tool_name} tool with parameters: {execute_request.parameters or {}}")
        
        return {
            "status": result.get("status", "error"),
            "tool_name": execute_request.tool_name,
            "parameters": execute_request.parameters or {},
            "result": result.get("response"),
            "tool_calls": result.get("tool_calls", [])
        }
        
    except Exception as e:
        return {
            "status": "error",
            "message": f"Tool execution failed: {str(e)}"
        } 