from typing import List, Dict, Any, Optional
from datetime import datetime
from render_relay.utils.get_logger import get_logger

from .mixins.session_mixin import SessionMixin
from .mixins.context_mixin import ContextMixin
from .mixins.message_mixin import MessageMixin
from .mixins.state_mixin import StateMixin
from .mixins.tool_mixin import ToolMixin
from ..config.config import config

logger = get_logger("session_service")

class SessionService(SessionMixin, ContextMixin, MessageMixin, StateMixin, ToolMixin):
    """Unified service for managing all session-related operations"""
    def __init__(self, 
                 db_service=None,
                 redis_service=None,
                 vector_service=None,
                 agent_service=None):
        
        # Initialize all mixins with their dependencies
        SessionMixin.__init__(self, db_service)
        ContextMixin.__init__(self, db_service, vector_service)
        MessageMixin.__init__(self, db_service)
        StateMixin.__init__(self, redis_service, db_service)
        ToolMixin.__init__(self, agent_service)
        
        # Store services for high-level operations
        self.db_service = db_service
        self.redis_service = redis_service
        self.vector_service = vector_service
        self.agent_service = agent_service
        self.logger = logger
    
    # High-level session operations that combine multiple mixins
    async def create_complete_session(self, session_id: str, initial_message: str = None, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """Create a complete session with all components"""
        try:
            self.logger.info(f"Creating complete session {session_id}")
            
            # Create base session
            session_created = await self.create_session(session_id)
            if not session_created:
                return {
                    "status": "error",
                    "message": "Failed to create base session"
                }
            
            # Store initial context if provided
            if context:
                context_stored = await self.store_context(session_id, context)
                if not context_stored:
                    self.logger.warning(f"Failed to store initial context for session {session_id}")
            
            # Add initial message if provided
            if initial_message:
                message_added = await self.add_message(session_id, "user", initial_message)
                if not message_added:
                    self.logger.warning(f"Failed to add initial message for session {session_id}")
            
            # Create initial agent state
            from ..db import AgentState
            agent_state = AgentState(session_id=session_id)
            state_saved = await self.save_agent_state(session_id, agent_state)
            if not state_saved:
                self.logger.warning(f"Failed to save initial agent state for session {session_id}")
            
            self.logger.info(f"Complete session {session_id} created successfully")
            return {
                "status": "success",
                "session_id": session_id,
                "message": "Complete session created successfully"
            }
        except Exception as e:
            self.logger.error(f"Error creating complete session {session_id}: {e}")
            return {
                "status": "error",
                "message": f"Failed to create complete session: {str(e)}"
            }
    
    async def get_session_summary(self, session_id: str) -> Dict[str, Any]:
        """Get comprehensive session summary"""
        try:
            self.logger.info(f"Getting session summary for {session_id}")
            
            session = await self.get_session(session_id)
            messages = await self.get_messages(session_id)
            context = await self.retrieve_context(session_id)
            agent_state = await self.get_agent_state(session_id)
            state_summary = await self.get_state_summary(session_id)
            
            return {
                "status": "success",
                "session_id": session_id,
                "session": session,
                "message_count": len(messages),
                "context_count": len(context),
                "agent_state": agent_state.to_dict() if agent_state else None,
                "state_summary": state_summary,
                "last_activity": session.get("updated_at") if session else None
            }
        except Exception as e:
            self.logger.error(f"Error getting session summary for {session_id}: {e}")
            return {
                "status": "error",
                "message": f"Failed to get session summary: {str(e)}"
            }
    
    async def delete_complete_session(self, session_id: str) -> Dict[str, Any]:
        """Delete session and all associated data"""
        try:
            self.logger.info(f"Deleting complete session {session_id}")
            
            # Delete from all storage layers
            session_deleted = await self.delete_session(session_id)
            context_deleted = await self.delete_context(session_id)
            messages_deleted = await self.delete_messages(session_id)
            state_deleted = await self.delete_agent_state(session_id)
            
            # Log any failures
            if not session_deleted:
                self.logger.warning(f"Failed to delete session {session_id} from database")
            if not context_deleted:
                self.logger.warning(f"Failed to delete context for session {session_id}")
            if not messages_deleted:
                self.logger.warning(f"Failed to delete messages for session {session_id}")
            if not state_deleted:
                self.logger.warning(f"Failed to delete agent state for session {session_id}")
            
            self.logger.info(f"Complete session {session_id} deleted")
            return {
                "status": "success",
                "session_id": session_id,
                "message": "Session completely deleted"
            }
        except Exception as e:
            self.logger.error(f"Error deleting complete session {session_id}: {e}")
            return {
                "status": "error",
                "message": f"Failed to delete session: {str(e)}"
            }
    
    async def add_message_to_session(self, session_id: str, role: str, content: str, metadata: Dict[str, Any] = None) -> Dict[str, Any]:
        """Add a message to a session and update agent state"""
        try:
            self.logger.info(f"Adding message to session {session_id}")
            
            # Add message to database
            message_added = await self.add_message(session_id, role, content, metadata)
            if not message_added:
                return {
                    "status": "error",
                    "message": "Failed to add message to database"
                }
            
            # Update agent state
            agent_state = await self.get_agent_state(session_id)
            if agent_state:
                # Add message to agent state
                from ..db import Message, MessageRole
                new_message = Message(
                    role=MessageRole(role),
                    content=content,
                    timestamp=datetime.now(),
                    metadata=metadata or {}
                )
                agent_state.messages.append(new_message)
                agent_state.updated_at = datetime.now()
                
                # Save updated state
                state_saved = await self.save_agent_state(session_id, agent_state)
                if not state_saved:
                    self.logger.warning(f"Failed to save updated agent state for session {session_id}")
            
            self.logger.info(f"Message added to session {session_id}")
            return {
                "status": "success",
                "session_id": session_id,
                "message": "Message added successfully"
            }
        except Exception as e:
            self.logger.error(f"Error adding message to session {session_id}: {e}")
            return {
                "status": "error",
                "message": f"Failed to add message: {str(e)}"
            }
    
    async def get_session_messages(self, session_id: str) -> Dict[str, Any]:
        """Get messages for a session with metadata"""
        try:
            self.logger.info(f"Getting messages for session {session_id}")
            
            messages = await self.get_messages(session_id)
            message_count = await self.get_message_count(session_id)
            last_message = await self.get_last_message(session_id)
            
            return {
                "status": "success",
                "session_id": session_id,
                "messages": messages,
                "message_count": message_count,
                "last_message": last_message
            }
        except Exception as e:
            self.logger.error(f"Error getting messages for session {session_id}: {e}")
            return {
                "status": "error",
                "message": f"Failed to get messages: {str(e)}"
            }
    
    async def list_all_sessions(self) -> Dict[str, Any]:
        """List all sessions with comprehensive information"""
        try:
            self.logger.info("Listing all sessions")
            
            # Get sessions from database
            db_sessions = await self.list_active_sessions()
            
            # Get active states from Redis
            active_states = await self.list_active_states()
            
            # Combine information
            session_list = []
            for session in db_sessions:
                session_id = session["session_id"]
                session_info = {
                    **session,
                    "is_active_in_redis": session_id in active_states,
                    "state_summary": await self.get_state_summary(session_id)
                }
                session_list.append(session_info)
            
            return {
                "status": "success",
                "sessions": session_list,
                "total_count": len(session_list),
                "active_in_redis": len(active_states)
            }
        except Exception as e:
            self.logger.error(f"Error listing all sessions: {e}")
            return {
                "status": "error",
                "message": f"Failed to list sessions: {str(e)}"
            }
    
