"""
Session Mixin for basic session management operations
"""

from typing import List, Dict, Any, Optional
from datetime import datetime
from render_relay.utils.get_logger import get_logger

logger = get_logger("session_mixin")

class SessionMixin:
    """Base session management functionality"""
    
    def __init__(self, db_service=None):
        self.db_service = db_service
        self.logger = logger
    
    async def create_session(self, session_id: str, meta_data: Dict[str, Any] = None) -> bool:
        """Create a new session"""
        try:
            if not self.db_service:
                raise AttributeError("SessionMixin requires db_service to be set")
            
            session_controller = await self.db_service.session_controller
            await session_controller.create_session(session_id, meta_data)
            self.logger.info(f"Created session {session_id}")
            return True
        except Exception as e:
            self.logger.error(f"Error creating session {session_id}: {e}")
            return False
    
    async def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get session by ID"""
        try:
            if not self.db_service:
                raise AttributeError("SessionMixin requires db_service to be set")
            
            session_controller = await self.db_service.session_controller
            session = await session_controller.get_session(session_id)
            
            if session:
                return {
                    "session_id": session.session_id,
                    "created_at": session.created_at.isoformat(),
                    "updated_at": session.updated_at.isoformat(),
                    "status": session.status,
                    "meta_data": session.meta_data
                }
            return None
        except Exception as e:
            self.logger.error(f"Error getting session {session_id}: {e}")
            return None
    
    async def update_session(self, session_id: str, **kwargs) -> bool:
        """Update session with provided fields"""
        try:
            if not self.db_service:
                raise AttributeError("SessionMixin requires db_service to be set")
            
            session_controller = await self.db_service.session_controller
            session = await session_controller.update_session(session_id, **kwargs)
            return session is not None
        except Exception as e:
            self.logger.error(f"Error updating session {session_id}: {e}")
            return False
    
    async def delete_session(self, session_id: str) -> bool:
        """Delete session"""
        try:
            if not self.db_service:
                raise AttributeError("SessionMixin requires db_service to be set")
            
            session_controller = await self.db_service.session_controller
            return await session_controller.delete_session(session_id)
        except Exception as e:
            self.logger.error(f"Error deleting session {session_id}: {e}")
            return False
    
    async def list_active_sessions(self) -> List[Dict[str, Any]]:
        """List all active sessions"""
        try:
            if not self.db_service:
                raise AttributeError("SessionMixin requires db_service to be set")
            
            session_controller = await self.db_service.session_controller
            sessions = await session_controller.list_active_sessions()
            
            session_list = []
            for session in sessions:
                session_list.append({
                    "session_id": session.session_id,
                    "created_at": session.created_at.isoformat(),
                    "updated_at": session.updated_at.isoformat(),
                    "status": session.status,
                    "meta_data": session.meta_data
                })
            
            return session_list
        except Exception as e:
            self.logger.error(f"Error listing sessions: {e}")
            return []
    
    async def mark_session_active(self, session_id: str) -> bool:
        """Mark session as active"""
        return await self.update_session(session_id, status='active')
    
    async def mark_session_deleted(self, session_id: str) -> bool:
        """Mark session as deleted"""
        return await self.update_session(session_id, status='deleted')
    
    async def get_session_count(self) -> int:
        """Get total number of sessions"""
        try:
            if not self.db_service:
                raise AttributeError("SessionMixin requires db_service to be set")
            
            session_controller = await self.db_service.session_controller
            return await session_controller.get_session_count()
        except Exception as e:
            self.logger.error(f"Error getting session count: {e}")
            return 0 