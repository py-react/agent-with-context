from fastapi import Request
from pydantic import BaseModel
from app.factory.workflow_factory import workflow_factory

class SendMessageRequest(BaseModel):
    session_id: str
    message: str

async def POST(request: Request, message_request: SendMessageRequest):
    """Send a message to an agent session"""
    # Get workflow service directly from workflow factory
    workflow = workflow_factory.get_agent_workflow()
    
    return await workflow.process_message(message_request.session_id, message_request.message) 