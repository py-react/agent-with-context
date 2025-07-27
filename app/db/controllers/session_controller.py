"""
Session Controller for managing session operations
"""

from typing import List, Dict, Any, Optional
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from render_relay.utils.get_logger import get_logger

from ..models import Session

logger = get_logger(__name__)


class SessionController:
    """Controller for managing session operations"""
    
    def __init__(self):
        """Initialize the controller - manages its own sessions"""
        self.logger = logger
    
    async def _get_session(self) -> AsyncSession:
        """Get a database session"""
        from ..config import AsyncSessionLocal
        async with AsyncSessionLocal() as session:
            return session
    
    async def create_session(self, session_id: str, metadata: Optional[Dict[str, Any]] = None) -> Session:
        """Create a new session"""
        db = await self._get_session()
        try:
            # Business logic: validate session ID
            if not self._validate_session_id(session_id):
                raise ValueError("Invalid session ID format")
            
            session = Session(
                session_id=session_id,
                meta_data=metadata or {"created_at": datetime.now().isoformat()}
            )
            
            db.add(session)
            await db.commit()
            await db.refresh(session)
            
            self.logger.info(f"Created session {session_id}")
            return session
            
        except Exception as e:
            self.logger.error(f"Failed to create session {session_id}: {e}")
            raise
        finally:
            await db.close()
    
    async def get_session(self, session_id: str) -> Optional[Session]:
        """Get a session by ID"""
        db = await self._get_session()
        try:
            stmt = select(Session).where(Session.session_id == session_id)
            result = await db.execute(stmt)
            return result.scalar_one_or_none()
            
        except Exception as e:
            self.logger.error(f"Failed to get session {session_id}: {e}")
            raise
        finally:
            await db.close()
    
    async def update_session(self, session_id: str, **kwargs) -> Optional[Session]:
        """Update a session"""
        db = await self._get_session()
        try:
            stmt = select(Session).where(Session.session_id == session_id)
            result = await db.execute(stmt)
            session = result.scalar_one_or_none()
            
            if not session:
                return None
            
            # Apply updates
            for key, value in kwargs.items():
                if hasattr(session, key):
                    setattr(session, key, value)
            
            session.updated_at = datetime.now()
            
            await db.commit()
            await db.refresh(session)
            
            self.logger.info(f"Updated session {session_id}")
            return session
            
        except Exception as e:
            self.logger.error(f"Failed to update session {session_id}: {e}")
            raise
        finally:
            await db.close()
    
    async def mark_session_active(self, session_id: str) -> bool:
        """Mark a session as active"""
        db = await self._get_session()
        try:
            stmt = select(Session).where(Session.session_id == session_id)
            result = await db.execute(stmt)
            session = result.scalar_one_or_none()
            
            if not session:
                return False
            
            session.status = 'active'
            session.updated_at = datetime.now()
            
            await db.commit()
            await db.refresh(session)
            
            self.logger.info(f"Marked session {session_id} as active")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to mark session {session_id} as active: {e}")
            raise
        finally:
            await db.close()
    
    async def mark_session_inactive(self, session_id: str) -> bool:
        """Mark a session as inactive"""
        db = await self._get_session()
        try:
            stmt = select(Session).where(Session.session_id == session_id)
            result = await db.execute(stmt)
            session = result.scalar_one_or_none()
            
            if not session:
                return False
            
            session.status = 'inactive'
            session.updated_at = datetime.now()
            
            await db.commit()
            await db.refresh(session)
            
            self.logger.info(f"Marked session {session_id} as inactive")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to mark session {session_id} as inactive: {e}")
            raise
        finally:
            await db.close()

    async def mark_session_deleted(self, session_id: str) -> bool:
        """Mark a session as deleted (soft delete)"""
        db = await self._get_session()
        try:
            stmt = select(Session).where(Session.session_id == session_id)
            result = await db.execute(stmt)
            session = result.scalar_one_or_none()
            
            if not session:
                return False
            
            session.status = 'deleted'
            session.updated_at = datetime.now()
            
            await db.commit()
            await db.refresh(session)
            
            self.logger.info(f"Marked session {session_id} as deleted")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to mark session {session_id} as deleted: {e}")
            raise
        finally:
            await db.close()

    async def delete_session(self, session_id: str) -> bool:
        """Delete a session (hard delete)"""
        db = await self._get_session()
        try:
            stmt = select(Session).where(Session.session_id == session_id)
            result = await db.execute(stmt)
            session = result.scalar_one_or_none()
            
            if not session:
                return False
            
            await db.delete(session)
            await db.commit()
            
            self.logger.info(f"Deleted session {session_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to delete session {session_id}: {e}")
            raise
        finally:
            await db.close()

    async def list_active_sessions(self, limit: Optional[int] = None) -> List[Session]:
        """List all active sessions"""
        db = await self._get_session()
        try:
            stmt = select(Session).where(Session.status == 'active').order_by(Session.updated_at.desc())
            if limit:
                stmt = stmt.limit(limit)
            
            result = await db.execute(stmt)
            return result.scalars().all()
            
        except Exception as e:
            self.logger.error(f"Failed to list active sessions: {e}")
            raise
        finally:
            await db.close()

    async def get_session_count(self) -> int:
        """Get the count of sessions"""
        db = await self._get_session()
        try:
            stmt = select(func.count(Session.session_id))
            result = await db.execute(stmt)
            return result.scalar()
            
        except Exception as e:
            self.logger.error(f"Failed to get session count: {e}")
            raise
        finally:
            await db.close()
    
    # Business Logic Methods
    def _validate_session_id(self, session_id: str) -> bool:
        """Validate session ID format"""
        if not session_id or not isinstance(session_id, str):
            return False
        
        if len(session_id.strip()) == 0:
            return False
        
        return True
    
    def _validate_session_status(self, status: str) -> bool:
        """Validate session status"""
        valid_statuses = ["active", "inactive", "deleted", "completed", "error"]
        return status in valid_statuses
    
    def _format_session_for_storage(self, session_id: str, meta_data: Dict[str, Any] = None) -> Dict[str, Any]:
        """Format session data for storage"""
        return {
            "session_id": session_id,
            "meta_data": meta_data or {"created_at": datetime.now().isoformat()}
        }
    
    def _format_session_for_response(self, session_data: Dict[str, Any]) -> Dict[str, Any]:
        """Format session data for API response"""
        return {
            "session_id": session_data.get("session_id"),
            "status": session_data.get("status"),
            "meta_data": session_data.get("meta_data"),
            "created_at": session_data.get("created_at"),
            "updated_at": session_data.get("updated_at")
        } 