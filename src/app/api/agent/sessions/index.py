from fastapi import Request
from app.factory.service_factory import service_factory

async def GET(request: Request):
    """List all active sessions"""
    try:
        # Get unified session service directly from service factory
        session_service = service_factory.get_service('session')
        
        result = await session_service.list_all_sessions()
        return result
        
    except Exception as e:
        return {
            "status": "error",
            "message": f"Failed to list sessions: {str(e)}"
        } 
    
async def DELETE(request: Request, session_id: str,soft_delete: bool = True):
    """Delete a session, soft delete by default"""
    try:
        # Get session service directly from service factory
        session_service = service_factory.get_service('session')
        
        # Delete session
        if soft_delete:
            await session_service.mark_session_deleted(session_id)
        else:
            await session_service.delete_session(session_id)
        
        return {
            "status": "success",
            "message": f"Session {session_id} deleted"
        }
        
    except Exception as e:
        return {
            "status": "error",
            "message": f"Failed to delete session: {str(e)}"
        }
    
async def PUT(request: Request, session_id: str):
    """Update a session (mark active)"""
    try:
        # Get session service directly from service factory
        session_service = service_factory.get_service('session')
        
        # Mark session as active
        await session_service.mark_session_active(session_id)

        return {
            "status": "success",
            "message": f"Session {session_id} marked as active"
        }
        
    except Exception as e:
        return {
            "status": "error",
            "message": f"Failed to mark session as active: {str(e)}"
        }