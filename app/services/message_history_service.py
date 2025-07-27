"""
Message History Service for managing conversation message history operations.
"""

import json
import asyncio
import concurrent.futures
from datetime import datetime
from typing import List, Dict, Any, Optional
from render_relay.utils.get_logger import get_logger
from ..db import MessageControllerSync
from ..config.config import config

logger = get_logger("message_history_service")

def _serialize_datetime(obj):
    """Helper function to serialize datetime objects for JSON"""
    if isinstance(obj, datetime):
        return obj.isoformat()
    elif isinstance(obj, dict):
        return {k: _serialize_datetime(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [_serialize_datetime(item) for item in obj]
    else:
        return obj

class MessageHistoryService:
    """Service for managing message history operations"""
    
    def __init__(self, redis_service=None):
        """Initialize the message history service"""
        self.logger = logger
        self.redis_service = redis_service
        self.logger.info("ℹ️ Message history service initialized with Redis and PostgreSQL support")
    
    def _run_async_in_thread(self, async_func, *args, **kwargs):
        """Helper method to run async functions in a thread"""
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            return loop.run_until_complete(async_func(*args, **kwargs))
        except Exception as e:
            self.logger.error(f"Error running async function in thread: {e}")
            raise e
        finally:
            loop.close()

    def _get_messages_from_redis(self, session_id: str) -> List[Dict[str, Any]]:
        """Get messages from Redis"""
        try:
            if not self.redis_service:
                self.logger.error("Redis service not available")
                raise RuntimeError("Redis service not available")
            
            # Use Redis call for tools
            result = self.redis_service.get_agent_state_for_tools(session_id)
            if result and hasattr(result, 'messages'):
                # Convert messages and ensure timestamps are serializable
                messages = []
                for msg in result.messages:
                    msg_dict = msg.dict()
                    # Ensure timestamp is serializable
                    if 'timestamp' in msg_dict and msg_dict['timestamp']:
                        if hasattr(msg_dict['timestamp'], 'isoformat'):
                            msg_dict['timestamp'] = msg_dict['timestamp'].isoformat()
                    messages.append(msg_dict)
                return messages
            return []
                
        except Exception as e:
            self.logger.error(f"Error getting messages from Redis: {e}")
            # Don't return empty list, raise the error to prevent fallback
            raise e

    def _get_messages_from_db_sync(self, session_id: str, limit: int = None) -> List[Dict[str, Any]]:
        """Get messages from PostgreSQL database using synchronous approach"""
        try:
            # Use the synchronous controller
            controller = MessageControllerSync()
            return controller.get_messages_sync(session_id, limit)
        except Exception as e:
            self.logger.error(f"Error getting messages from database: {e}")
            # Don't return empty list, raise the error to prevent fallback
            raise e
    
    def get_previous_messages(self, session_id: str = None, source: str = "auto") -> str:
        """
        Retrieve previous conversation messages for a session.
        
        Args:
            session_id: The session ID to get messages for
            source: Source to get messages from - "redis", "database", or "auto" (default: "auto")
        
        Returns:
            JSON string containing the conversation messages with metadata
        """
        try:
            # Use config limit directly
            limit = config.DEFAULT_MESSAGE_LIMIT
            
            # Debug logging to see what parameters are being passed
            self.logger.info(f"🔍 get_previous_messages called with session_id={session_id}, limit={limit}, source={source}")
            
            # Handle missing session_id gracefully
            if not session_id:
                self.logger.warning("❌ get_previous_messages called without session_id")
                return json.dumps({
                    "status": "error",
                    "message": "Session ID is required but not provided",
                    "messages": [],
                    "source": source,
                    "session_id": None
                })
            
            self.logger.info(f"🔍 Getting previous messages for session {session_id}, limit: {limit}, source: {source}")
            
            # Get messages based on source preference
            messages = []
            
            # Try Redis first if available and requested
            if source == "redis" or source == "auto":
                try:
                    messages = self._get_messages_from_redis(session_id)
                    if messages:
                        self.logger.info(f"✅ Retrieved {len(messages)} messages from Redis")
                        source_used = "redis"
                    else:
                        self.logger.warning("No messages found in Redis")
                except Exception as e:
                    self.logger.error(f"Failed to get messages from Redis: {e}")
                    if source == "redis":
                        # If Redis is the only source, return error
                        return json.dumps({
                            "status": "error",
                            "message": f"Failed to retrieve messages from Redis: {str(e)}",
                            "messages": [],
                            "source": "redis",
                            "session_id": session_id
                        })
                    # If auto mode, continue to try database
            
            # Fallback to database if no messages from Redis
            if not messages and (source == "auto" or source == "database"):
                try:
                    # Try database
                    messages = self._get_messages_from_db_sync(session_id, limit)
                    if messages:
                        self.logger.info(f"✅ Retrieved {len(messages)} messages from database")
                        source_used = "database"
                    else:
                        self.logger.warning("No messages found in database")
                except Exception as e:
                    self.logger.error(f"Failed to get messages from database: {e}")
                    if source == "database":
                        # If database is the only source, return error
                        return json.dumps({
                            "status": "error",
                            "message": f"Failed to retrieve messages from database: {str(e)}",
                            "messages": [],
                            "source": "database",
                            "session_id": session_id
                        })
            
            if not messages:
                return json.dumps({
                    "status": "warning",
                    "message": "No messages found for this session",
                    "messages": [],
                    "source": source,
                    "session_id": session_id
                })
            
            # Return full messages
            response_data = {
                "status": "success",
                "message": f"Retrieved {len(messages)} messages",
                "messages": messages,
                "message_count": len(messages),
                "source": source_used if 'source_used' in locals() else source,
                "session_id": session_id,
                "retrieved_at": datetime.now().isoformat()
            }
            
            # Ensure all datetime objects are properly serialized
            serialized_data = _serialize_datetime(response_data)
            
            return json.dumps(serialized_data, indent=2)
            
        except Exception as e:
            self.logger.error(f"Error getting previous messages: {e}")
            return json.dumps({
                "status": "error",
                "message": f"Failed to retrieve messages: {str(e)}",
                "messages": [],
                "source": source,
                "session_id": session_id
            })
    

    

    
 