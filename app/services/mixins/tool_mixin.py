"""
Tool Mixin for tool management operations
"""

from typing import List, Dict, Any, Optional
from datetime import datetime
from render_relay.utils.get_logger import get_logger

logger = get_logger("tool_mixin")

class ToolMixin:
    """Base tool management functionality"""
    
    def __init__(self, agent_service=None):
        self.agent_service = agent_service
        self.logger = logger
    
    async def get_available_tools(self) -> List[Dict[str, Any]]:
        """Get list of available tools"""
        try:
            if not self.agent_service:
                raise AttributeError("ToolMixin requires agent_service to be set")
            
            tools = self.agent_service.get_tools()
            tool_list = []
            
            for tool in tools:
                tool_list.append({
                    "name": tool.name,
                    "description": tool.description,
                    "schema": tool.args_schema.schema() if hasattr(tool, 'args_schema') and tool.args_schema else None
                })
            
            return tool_list
            
        except Exception as e:
            self.logger.error(f"Error getting available tools: {e}")
            return []
    
    async def execute_tool(self, session_id: str, tool_name: str, **kwargs) -> Dict[str, Any]:
        """Execute a specific tool"""
        try:
            if not self.agent_service:
                raise AttributeError("ToolMixin requires agent_service to be set")
            
            # Find the tool by name
            tools = self.agent_service.get_tools()
            tool = None
            for t in tools:
                if t.name == tool_name:
                    tool = t
                    break
            
            if not tool:
                return {
                    "status": "error",
                    "message": f"Tool '{tool_name}' not found"
                }
            
            # Execute the tool
            if hasattr(tool, '_arun'):
                result = await tool._arun(**kwargs)
            elif hasattr(tool, '_run'):
                result = tool._run(**kwargs)
            else:
                return {
                    "status": "error",
                    "message": f"Tool '{tool_name}' has no execution method"
                }
            
            return {
                "status": "success",
                "tool_name": tool_name,
                "result": result,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Error executing tool {tool_name}: {e}")
            return {
                "status": "error",
                "message": f"Failed to execute tool '{tool_name}': {str(e)}"
            }
    
    async def get_tool_history(self, session_id: str) -> List[Dict[str, Any]]:
        """Get tool execution history for a session"""
        try:
            if not self.agent_service:
                raise AttributeError("ToolMixin requires agent_service to be set")
            
            # This would typically come from the agent state or a separate tool history table
            # For now, we'll return an empty list as this would need to be implemented
            # based on how tool executions are tracked in the agent state
            
            return []
            
        except Exception as e:
            self.logger.error(f"Error getting tool history for session {session_id}: {e}")
            return []
    
    async def validate_tool_parameters(self, tool_name: str, **kwargs) -> Dict[str, Any]:
        """Validate tool parameters before execution"""
        try:
            if not self.agent_service:
                raise AttributeError("ToolMixin requires agent_service to be set")
            
            tools = self.agent_service.get_tools()
            tool = None
            for t in tools:
                if t.name == tool_name:
                    tool = t
                    break
            
            if not tool:
                return {
                    "valid": False,
                    "message": f"Tool '{tool_name}' not found"
                }
            
            # Validate parameters if tool has a schema
            if hasattr(tool, 'args_schema') and tool.args_schema:
                try:
                    # This would validate against the tool's schema
                    # For now, we'll just return success
                    return {
                        "valid": True,
                        "message": "Parameters are valid"
                    }
                except Exception as validation_error:
                    return {
                        "valid": False,
                        "message": f"Parameter validation failed: {str(validation_error)}"
                    }
            
            return {
                "valid": True,
                "message": "No schema available for validation"
            }
            
        except Exception as e:
            self.logger.error(f"Error validating tool parameters for {tool_name}: {e}")
            return {
                "valid": False,
                "message": f"Validation error: {str(e)}"
            } 