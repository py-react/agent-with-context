"""
Context Mixin for context management operations
"""

from typing import List, Dict, Any, Optional
from datetime import datetime
from render_relay.utils.get_logger import get_logger
from ...config.config import config

logger = get_logger("context_mixin")

class ContextMixin:
    """Base context management functionality"""
    
    def __init__(self, db_service=None, vector_service=None):
        self.db_service = db_service
        self.vector_service = vector_service
        self.logger = logger
    
    async def store_context(self, session_id: str, context_data: Dict[str, Any]) -> bool:
        """Store context data"""
        try:
            if not self.vector_service:
                raise AttributeError("ContextMixin requires vector_service to be set")
            
            # Ensure session exists first
            if self.db_service:
                session_controller = await self.db_service.session_controller
                session = await session_controller.get_session(session_id)
                if not session:
                    await session_controller.create_session(
                        session_id=session_id,
                        metadata={"last_context_update": datetime.now().isoformat()}
                    )
                else:
                    await session_controller.update_session(
                        session_id=session_id,
                        meta_data={"last_context_update": datetime.now().isoformat()}
                    )
            
            # Store context using vector service
            return await self.vector_service.store_context(session_id, context_data)
            
        except Exception as e:
            self.logger.error(f"Error storing context for session {session_id}: {e}")
            return False
    
    async def retrieve_context(self, session_id: str, query: str = None) -> List[Dict[str, Any]]:
        """Retrieve context"""
        try:
            if not self.vector_service:
                raise AttributeError("ContextMixin requires vector_service to be set")
            
            if query:
                # Semantic search
                return await self.vector_service.retrieve_context(session_id, query)
            else:
                # Get all context
                return await self.vector_service.retrieve_context(session_id)
                
        except Exception as e:
            self.logger.error(f"Error retrieving context for session {session_id}: {e}")
            return []
    
    async def delete_context(self, session_id: str, context_key: str = None) -> bool:
        """Delete context for a session"""
        try:
            if not self.vector_service:
                raise AttributeError("ContextMixin requires vector_service to be set")
            
            if context_key:
                # Use context controller directly for key-based deletion
                context_controller = await self.db_service.context_controller
                return await context_controller.delete_context_by_key(session_id, context_key)
            else:
                return await self.vector_service.delete_session_context(session_id)
                
        except Exception as e:
            self.logger.error(f"Error deleting context for session {session_id}: {e}")
            return False
    
    async def get_context_stats(self, session_id: str) -> Dict[str, Any]:
        """Get context statistics for a session"""
        try:
            if not self.vector_service:
                raise AttributeError("ContextMixin requires vector_service to be set")
            
            return await self.vector_service.get_session_stats(session_id)
            
        except Exception as e:
            self.logger.error(f"Error getting context stats for session {session_id}: {e}")
            return {"total_contexts": 0, "session_id": session_id} 