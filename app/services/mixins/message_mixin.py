"""
Message Mixin for message management operations
"""

from typing import List, Dict, Any, Optional
from datetime import datetime
from render_relay.utils.get_logger import get_logger
from ...config.config import config

logger = get_logger("message_mixin")

class MessageMixin:
    """Base message management functionality"""
    
    def __init__(self, db_service=None):
        self.db_service = db_service
        self.logger = logger
    
    async def add_message(self, session_id: str, role: str, content: str, metadata: Dict[str, Any] = None) -> bool:
        """Add a message to a session"""
        try:
            if not self.db_service:
                raise AttributeError("MessageMixin requires db_service to be set")
            
            message_controller = await self.db_service.message_controller
            await message_controller.add_message(
                session_id=session_id,
                role=role,
                content=content,
                metadata=metadata
            )
            
            # Update session metadata
            session_controller = await self.db_service.session_controller
            await session_controller.update_session(
                session_id=session_id,
                message_count=await self.get_message_count(session_id),
                last_message_at=datetime.now()
            )
            
            self.logger.info(f"Added message to session {session_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error adding message to session {session_id}: {e}")
            return False
    
    async def get_messages(self, session_id: str) -> List[Dict[str, Any]]:
        """Get messages for a session"""
        try:
            if not self.db_service:
                raise AttributeError("MessageMixin requires db_service to be set")
            
            message_controller = await self.db_service.message_controller
            messages = await message_controller.get_messages_by_session(session_id, config.SESSION_MESSAGE_LIMIT)
            
            message_list = []
            for msg in messages:
                message_list.append({
                    "id": msg.id,
                    "role": msg.role,
                    "content": msg.content,
                    "timestamp": msg.timestamp.isoformat() if msg.timestamp else None,
                    "metadata": msg.message_metadata
                })
            
            return message_list
            
        except Exception as e:
            self.logger.error(f"Error getting messages for session {session_id}: {e}")
            return []
    
    async def delete_messages(self, session_id: str) -> bool:
        """Delete all messages for a session"""
        try:
            if not self.db_service:
                raise AttributeError("MessageMixin requires db_service to be set")
            
            message_controller = await self.db_service.message_controller
            return await message_controller.delete_messages_by_session(session_id)
            
        except Exception as e:
            self.logger.error(f"Error deleting messages for session {session_id}: {e}")
            return False
    
    async def get_message_count(self, session_id: str) -> int:
        """Get message count for a session"""
        try:
            if not self.db_service:
                raise AttributeError("MessageMixin requires db_service to be set")
            
            message_controller = await self.db_service.message_controller
            return await message_controller.get_message_count(session_id)
            
        except Exception as e:
            self.logger.error(f"Error getting message count for session {session_id}: {e}")
            return 0
    
    async def get_last_message(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get the last message for a session"""
        try:
            if not self.db_service:
                raise AttributeError("MessageMixin requires db_service to be set")
            
            message_controller = await self.db_service.message_controller
            message = await message_controller.get_last_message(session_id)
            
            if message:
                return {
                    "id": message.id,
                    "role": message.role,
                    "content": message.content,
                    "timestamp": message.timestamp.isoformat() if message.timestamp else None,
                    "metadata": message.message_metadata
                }
            return None
            
        except Exception as e:
            self.logger.error(f"Error getting last message for session {session_id}: {e}")
            return None 