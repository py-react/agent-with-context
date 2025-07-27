"""
Message Controller for managing conversation message operations
"""

from typing import List, Dict, Any, Optional
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, delete
from sqlalchemy.orm import sessionmaker

from ..models import ConversationMessage
import json
from ..database import sync_engine
from ...config.config import config

# Create sync session factory using the existing sync engine
SyncSessionLocal = sessionmaker(
    sync_engine,
    expire_on_commit=False
)


class MessageController:
    """Controller for managing conversation message operations"""
    
    def __init__(self):
        """Initialize the controller - manages its own sessions"""
        pass
    
    async def _get_session(self) -> AsyncSession:
        """Get a database session"""
        from ..config import AsyncSessionLocal
        async with AsyncSessionLocal() as session:
            return session
    
    async def add_message(self, session_id: str, role: str, content: str, metadata: Dict[str, Any] = None) -> ConversationMessage:
        """Add a new message to the conversation"""
        db = await self._get_session()
        try:
            # Business logic: validate message data
            if not self._validate_message(role, content):
                raise ValueError("Invalid message data")
            
            # Get the next message order
            stmt = select(func.max(ConversationMessage.message_order)).where(
                ConversationMessage.session_id == session_id
            )
            result = await db.execute(stmt)
            max_order = result.scalar() or 0
            next_order = max_order + 1
            
            # Business logic: format message data
            message_data = self._format_message_for_storage(session_id, role, content, metadata, next_order)
            
            message = ConversationMessage(**message_data)
            db.add(message)
            await db.commit()
            await db.refresh(message)
            return message
        finally:
            await db.close()
    
    async def get_messages_by_session(self, session_id: str, limit: int = None) -> List[ConversationMessage]:
        """Get all messages for a session in order"""
        db = await self._get_session()
        try:
            stmt = select(ConversationMessage).where(
                ConversationMessage.session_id == session_id
            ).order_by(ConversationMessage.message_order.asc())
            
            if limit:
                stmt = stmt.limit(limit)
            
            result = await db.execute(stmt)
            return result.scalars().all()
        finally:
            await db.close()
    
    async def get_message_by_id(self, message_id: int) -> Optional[ConversationMessage]:
        """Get a specific message by ID"""
        db = await self._get_session()
        try:
            stmt = select(ConversationMessage).where(ConversationMessage.id == message_id)
            result = await db.execute(stmt)
            return result.scalar_one_or_none()
        finally:
            await db.close()
    
    async def update_message(self, message_id: int, **kwargs) -> Optional[ConversationMessage]:
        """Update a message with provided fields"""
        db = await self._get_session()
        try:
            stmt = select(ConversationMessage).where(ConversationMessage.id == message_id)
            result = await db.execute(stmt)
            message = result.scalar_one_or_none()
            
            if message:
                for key, value in kwargs.items():
                    if hasattr(message, key):
                        setattr(message, key, value)
                await db.commit()
                await db.refresh(message)
            return message
        finally:
            await db.close()
    
    async def delete_message(self, message_id: int) -> bool:
        """Delete a specific message"""
        db = await self._get_session()
        try:
            stmt = select(ConversationMessage).where(ConversationMessage.id == message_id)
            result = await db.execute(stmt)
            message = result.scalar_one_or_none()
            
            if message:
                await db.delete(message)
                await db.commit()
                return True
            return False
        except Exception as e:
            await db.rollback()
            raise e
        finally:
            await db.close()
    
    async def delete_messages_by_session(self, session_id: str) -> bool:
        """Delete all messages for a session"""
        db = await self._get_session()
        try:
            stmt = delete(ConversationMessage).where(
                ConversationMessage.session_id == session_id
            )
            await db.execute(stmt)
            await db.commit()
            return True
        except Exception as e:
            await db.rollback()
            raise e
        finally:
            await db.close()
    
    async def get_message_count(self, session_id: str) -> int:
        """Get the total number of messages for a session"""
        db = await self._get_session()
        try:
            stmt = select(func.count(ConversationMessage.id)).where(
                ConversationMessage.session_id == session_id
            )
            result = await db.execute(stmt)
            return result.scalar()
        finally:
            await db.close()
    
    async def get_last_message(self, session_id: str) -> Optional[ConversationMessage]:
        """Get the last message for a session"""
        db = await self._get_session()
        try:
            stmt = select(ConversationMessage).where(
                ConversationMessage.session_id == session_id
            ).order_by(ConversationMessage.message_order.desc()).limit(1)
            
            result = await db.execute(stmt)
            return result.scalar_one_or_none()
        finally:
            await db.close()
    
    async def get_messages_by_role(self, session_id: str, role: str, limit: int = None) -> List[ConversationMessage]:
        """Get messages by role for a session using business logic filtering"""
        # Get all messages for session
        all_messages = await self.get_messages_by_session(session_id)
        
        # Business logic: filter by role
        filtered_messages = [msg for msg in all_messages if msg.role == role]
        
        if limit:
            filtered_messages = filtered_messages[:limit]
        
        return filtered_messages
    
    def _validate_message(self, role: str, content: str) -> bool:
        """Validate message data"""
        if not role or not content:
            return False
        
        valid_roles = ["user", "assistant", "system"]
        if role not in valid_roles:
            return False
        
        if len(content.strip()) == 0:
            return False
        
        return True
    
    def _format_message_for_storage(self, session_id: str, role: str, content: str, 
                                   metadata: Dict[str, Any] = None, message_order: int = None) -> Dict[str, Any]:
        """Format message data for storage"""
        return {
            "session_id": session_id,
            "role": role,
            "content": content,
            "message_metadata": metadata or {},
            "message_order": message_order or 1
        }
    
    def _format_message_for_response(self, message_data: Dict[str, Any]) -> Dict[str, Any]:
        """Format message data for API response"""
        return {
            "id": message_data.get("id"),
            "session_id": message_data.get("session_id"),
            "role": message_data.get("role"),
            "content": message_data.get("content"),
            "message_metadata": message_data.get("message_metadata"),
            "message_order": message_data.get("message_order"),
            "created_at": message_data.get("created_at"),
            "updated_at": message_data.get("updated_at")
        }
    
    def _calculate_next_message_order(self, existing_messages: List[Dict[str, Any]]) -> int:
        """Calculate the next message order number"""
        if not existing_messages:
            return 1
        
        max_order = max(msg.get("message_order", 0) for msg in existing_messages)
        return max_order + 1
    
    def _filter_messages_by_role(self, messages: List[Dict[str, Any]], role: str) -> List[Dict[str, Any]]:
        """Filter messages by role"""
        return [msg for msg in messages if msg.get("role") == role]
    
    def _get_conversation_summary(self, messages: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Generate a summary of the conversation"""
        if not messages:
            return {"total_messages": 0, "roles": {}, "last_message": None}
        
        roles = {}
        for msg in messages:
            role = msg.get("role", "unknown")
            roles[role] = roles.get(role, 0) + 1
        
        return {
            "total_messages": len(messages),
            "roles": roles,
            "last_message": messages[-1] if messages else None
        }
    
    def _search_messages(self, messages: List[Dict[str, Any]], query: str, limit: int = None) -> List[Dict[str, Any]]:
        """Search messages by content"""
        # Use config limit if not provided
        if limit is None:
            limit = config.DEFAULT_SEARCH_LIMIT
            
        if not query:
            return messages[:limit]
        
        query_lower = query.lower()
        matching_messages = []
        
        for msg in messages:
            content = msg.get("content", "").lower()
            if query_lower in content:
                matching_messages.append(msg)
        
        return matching_messages[:limit]
    
    def _get_conversation_topics(self, messages: List[Dict[str, Any]]) -> List[str]:
        """Extract conversation topics from messages"""
        # Simple topic extraction - in a real implementation, you might use NLP
        topics = set()
        for msg in messages:
            content = msg.get("content", "")
            # Extract potential topics (simple keyword-based approach)
            words = content.lower().split()
            for word in words:
                if len(word) > 4 and word.isalpha():
                    topics.add(word)
        
        return list(topics)[:10]  # Return top 10 topics
    
    def _validate_session_id(self, session_id: str) -> bool:
        """Validate session ID format"""
        if not session_id or not isinstance(session_id, str):
            return False
        
        if len(session_id.strip()) == 0:
            return False
        
        return True


class MessageControllerSync:
    """Synchronous controller for managing conversation messages to avoid event loop conflicts"""
    
    def __init__(self):
        """Initialize the synchronous controller"""
        pass
    
    def get_messages_sync(self, session_id: str, limit: int = None) -> List[Dict[str, Any]]:
        """Get messages from PostgreSQL database using synchronous approach"""
        try:
            with SyncSessionLocal() as db:
                # Build query
                stmt = select(ConversationMessage).where(
                    ConversationMessage.session_id == session_id
                ).order_by(ConversationMessage.message_order.asc())
                
                if limit:
                    stmt = stmt.limit(limit)
                
                result = db.execute(stmt)
                messages = result.scalars().all()
                
                # Convert to dictionary format
                message_list = []
                for msg in messages:
                    message_list.append({
                        "id": msg.id,
                        "session_id": msg.session_id,
                        "role": msg.role,
                        "content": msg.content,
                        "message_metadata": msg.message_metadata,
                        "message_order": msg.message_order,
                        "timestamp": msg.timestamp.isoformat() if msg.timestamp else None
                    })
                
                return message_list
                
        except Exception as e:
            print(f"Database error in get_messages_sync: {str(e)}")
            # Don't return empty list, raise the error to prevent fallback
            raise e
    
    def add_message_sync(self, session_id: str, role: str, content: str, metadata: Dict[str, Any] = None) -> Dict[str, Any]:
        """Add a new message using synchronous operations"""
        try:
            with SyncSessionLocal() as db:
                # Get the next message order
                stmt = select(func.max(ConversationMessage.message_order)).where(
                    ConversationMessage.session_id == session_id
                )
                result = db.execute(stmt)
                max_order = result.scalar() or 0
                next_order = max_order + 1
                
                message = ConversationMessage(
                    session_id=session_id,
                    role=role,
                    content=content,
                    message_metadata=metadata,
                    message_order=next_order
                )
                db.add(message)
                db.commit()
                db.refresh(message)
                
                return {
                    "id": message.id,
                    "session_id": message.session_id,
                    "role": message.role,
                    "content": message.content,
                    "message_metadata": message.message_metadata,
                    "message_order": message.message_order,
                    "timestamp": message.timestamp.isoformat() if message.timestamp else None
                }
                
        except Exception as e:
            print(f"Database error in add_message_sync: {str(e)}")
            raise e
    
    def get_message_count_sync(self, session_id: str) -> int:
        """Get message count using synchronous operations"""
        try:
            with SyncSessionLocal() as db:
                stmt = select(func.count(ConversationMessage.id)).where(
                    ConversationMessage.session_id == session_id
                )
                result = db.execute(stmt)
                return result.scalar()
                
        except Exception as e:
            print(f"Database error in get_message_count_sync: {str(e)}")
            raise e
    
    def get_last_message_sync(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get the last message using synchronous operations"""
        try:
            with SyncSessionLocal() as db:
                stmt = select(ConversationMessage).where(
                    ConversationMessage.session_id == session_id
                ).order_by(ConversationMessage.message_order.desc()).limit(1)
                
                result = db.execute(stmt)
                message = result.scalar_one_or_none()
                
                if message:
                    return {
                        "id": message.id,
                        "session_id": message.session_id,
                        "role": message.role,
                        "content": message.content,
                        "message_metadata": message.message_metadata,
                        "message_order": message.message_order,
                        "timestamp": message.timestamp.isoformat() if message.timestamp else None
                    }
                return None
                
        except Exception as e:
            print(f"Database error in get_last_message_sync: {str(e)}")
            raise e 