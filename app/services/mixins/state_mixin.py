"""
State Mixin for agent state management operations
"""

from typing import List, Dict, Any, Optional
from datetime import datetime
from render_relay.utils.get_logger import get_logger

logger = get_logger("state_mixin")

class StateMixin:
    """Base state management functionality (Redis + PostgreSQL)"""
    
    def __init__(self, redis_service=None, db_service=None):
        self.redis_service = redis_service
        self.db_service = db_service
        self.logger = logger
    
    async def save_agent_state(self, session_id: str, state) -> bool:
        """Save agent state to Redis with write-through to PostgreSQL"""
        try:
            if not self.redis_service:
                raise AttributeError("StateMixin requires redis_service to be set")
            
            return await self.redis_service.save_agent_state(session_id, state)
            
        except Exception as e:
            self.logger.error(f"Error saving agent state for session {session_id}: {e}")
            return False
    
    async def get_agent_state(self, session_id: str):
        """Get agent state from Redis with fallback to PostgreSQL"""
        try:
            if not self.redis_service:
                raise AttributeError("StateMixin requires redis_service to be set")
            
            return await self.redis_service.get_agent_state(session_id)
            
        except Exception as e:
            self.logger.error(f"Error getting agent state for session {session_id}: {e}")
            return None
    
    async def delete_agent_state(self, session_id: str) -> bool:
        """Delete agent state from Redis"""
        try:
            if not self.redis_service:
                raise AttributeError("StateMixin requires redis_service to be set")
            
            return await self.redis_service.delete_agent_state(session_id)
            
        except Exception as e:
            self.logger.error(f"Error deleting agent state for session {session_id}: {e}")
            return False
    
    async def list_active_states(self) -> List[str]:
        """List all active agent sessions in Redis"""
        try:
            if not self.redis_service:
                raise AttributeError("StateMixin requires redis_service to be set")
            
            return await self.redis_service.list_active_sessions()
            
        except Exception as e:
            self.logger.error(f"Error listing active states: {e}")
            return []
    
    async def update_agent_state(self, session_id: str, **kwargs) -> bool:
        """Update agent state with new values"""
        try:
            if not self.redis_service:
                raise AttributeError("StateMixin requires redis_service to be set")
            
            # Get current state
            current_state = await self.get_agent_state(session_id)
            if not current_state:
                self.logger.error(f"No agent state found for session {session_id}")
                return False
            
            # Update state attributes
            for key, value in kwargs.items():
                if hasattr(current_state, key):
                    setattr(current_state, key, value)
            
            # Save updated state
            return await self.save_agent_state(session_id, current_state)
            
        except Exception as e:
            self.logger.error(f"Error updating agent state for session {session_id}: {e}")
            return False
    
    async def get_state_summary(self, session_id: str) -> Dict[str, Any]:
        """Get a summary of the agent state"""
        try:
            if not self.redis_service:
                raise AttributeError("StateMixin requires redis_service to be set")
            
            state = await self.get_agent_state(session_id)
            if not state:
                return {
                    "session_id": session_id,
                    "status": "not_found",
                    "message_count": 0,
                    "created_at": None,
                    "updated_at": None
                }
            
            return {
                "session_id": session_id,
                "status": state.status.value if hasattr(state.status, 'value') else str(state.status),
                "message_count": len(state.messages) if hasattr(state, 'messages') else 0,
                "created_at": state.created_at.isoformat() if state.created_at else None,
                "updated_at": state.updated_at.isoformat() if state.updated_at else None,
                "context_keys": list(state.context.keys()) if hasattr(state, 'context') else []
            }
            
        except Exception as e:
            self.logger.error(f"Error getting state summary for session {session_id}: {e}")
            return {
                "session_id": session_id,
                "status": "error",
                "message": str(e)
            } 