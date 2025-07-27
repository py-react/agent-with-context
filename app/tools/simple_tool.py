"""
Simple Tool for basic operations.
"""

from typing import Dict, Any, Optional
from render_relay.utils.get_logger import get_logger

logger = get_logger(__name__)


class SimpleTool:
    """A simple tool for basic operations."""
    
    def __init__(self):
        """Initialize the simple tool."""
        self.logger = logger
    
    def execute(self, operation: str, data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Execute a simple operation."""
        self.logger.info(f"Executing simple operation: {operation}")
        
        if operation == "echo":
            return {"result": data.get("message", "Hello World!")}
        elif operation == "add":
            a = data.get("a", 0)
            b = data.get("b", 0)
            return {"result": a + b}
        elif operation == "multiply":
            a = data.get("a", 1)
            b = data.get("b", 1)
            return {"result": a * b}
        else:
            return {"error": f"Unknown operation: {operation}"}
    
    def get_available_operations(self) -> list:
        """Get list of available operations."""
        return ["echo", "add", "multiply"]
    
    def get_operation_description(self, operation: str) -> str:
        """Get description of an operation."""
        descriptions = {
            "echo": "Echo back a message",
            "add": "Add two numbers",
            "multiply": "Multiply two numbers"
        }
        return descriptions.get(operation, "Unknown operation") 