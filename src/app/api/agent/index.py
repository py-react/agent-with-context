from fastapi import Request
from pydantic import BaseModel
from app.factory.service_factory import service_factory
from app.factory.workflow_factory import workflow_factory
import uuid
from typing import Optional, Dict, Any

class CreateSessionRequest(BaseModel):
    initial_message: Optional[str] = None
    context: Optional[Dict[str, Any]] = None

async def POST(request: Request, create_request: CreateSessionRequest):
    """Create a new agent session with optional initial context"""
    try:
        # Get workflow service directly from workflow factory
        workflow = workflow_factory.get_agent_workflow()
        
        # Create session with the initial message
        session_result = await workflow.create_session(
            create_request.initial_message,
            create_request.context
        )
        
        if session_result["status"] == "error":
            return session_result
        
        return {
            "status": "success",
            "session_id": session_result["session_id"],
            "message": "Session created successfully",
            "context": session_result.get("context", {}),
            "agent_state": session_result["agent_state"]
        }
        
    except Exception as e:
        return {
            "status": "error",
            "message": f"Failed to create session: {str(e)}"
        }

async def GET(request: Request, session_id: str):
    """Get agent session information"""
    
    try:
        # Get unified session service directly from service factory
        session_service = service_factory.get_service('session')
        
        summary = await session_service.get_session_summary(session_id)
        return summary
        
    except Exception as e:
        return {
            "status": "error",
            "message": f"Failed to retrieve session: {str(e)}"
        }

async def DELETE(request: Request, session_id: str):
    """Delete an agent session"""
    
    try:
        # Get unified session service directly from service factory
        session_service = service_factory.get_service('session')
        
        result = await session_service.delete_complete_session(session_id)
        return result
        
    except Exception as e:
        return {
            "status": "error",
            "message": f"Failed to delete session: {str(e)}"
        } 