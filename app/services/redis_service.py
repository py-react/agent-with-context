import time
import redis.asyncio as redis
import os
from typing import Optional, List
import json
from render_relay.utils.get_logger import get_logger
from ..db import AgentState
from .db_service import DatabaseService

logger = get_logger("redis_service")

class RedisService:
    def __init__(self, db_service: Optional[DatabaseService] = None):
        self.db_service = db_service
        from ..config.config import config
        self.redis_url = config.REDIS_URL
        self.redis_client: Optional[redis.Redis] = None
    
    async def connect(self):
        """Initialize Redis connection"""
        if not self.redis_client:
            start_time = time.time()
            logger.debug("🔌 Connecting to Redis...")
            self.redis_client = redis.from_url(self.redis_url, decode_responses=True)
            await self.redis_client.ping()
            connect_time = time.time() - start_time
            logger.debug(f"Redis connected successfully in {connect_time:.3f}s")
            logger.info("Redis connected successfully")
    
    async def disconnect(self):
        """Close Redis connection"""
        if self.redis_client:
            await self.redis_client.close()
            logger.info("Redis disconnected successfully")
    
    async def test_connection(self) -> bool:
        """Test if Redis connection is working"""
        try:
            await self.connect()
            await self.redis_client.ping()
            return True
        except Exception as e:
            logger.error(f"Redis connection failed: {e}")
            # Don't return False, raise the error to prevent fallback
            raise e
    
    async def set_key(self, key: str, value: str, ttl: int = 3600) -> bool:
        """Set a key with TTL"""
        try:
            await self.connect()
            await self.redis_client.setex(key, ttl, value)
            return True
        except Exception as e:
            logger.error(f"Error setting key {key}: {e}")
            # Don't return False, raise the error to prevent fallback
            raise e
    
    async def get_key(self, key: str) -> Optional[str]:
        """Get a key value"""
        try:
            await self.connect()
            return await self.redis_client.get(key)
        except Exception as e:
            logger.error(f"Error getting key {key}: {e}")
            # Don't return None, raise the error to prevent fallback
            raise e
    
    async def delete_key(self, key: str) -> bool:
        """Delete a key"""
        try:
            await self.connect()
            await self.redis_client.delete(key)
            return True
        except Exception as e:
            logger.error(f"Error deleting key {key}: {e}")
            # Don't return False, raise the error to prevent fallback
            raise e
        
    # Agent State specific methods
    async def save_agent_state(self, session_id: str, state: AgentState) -> bool:
        """Save agent state to Redis with write-through to PostgreSQL"""
        start_time = time.time()
        logger.debug(f"💾 Saving agent state for session {session_id}...")
        
        try:
            # 1. Save to Redis (fast access)
            await self.connect()
            state_dict = state.to_dict()
            state_json = json.dumps(state_dict, default=str)  # Fix: handle datetime serialization
            await self.redis_client.setex(
                f"agent_state:{session_id}",
                3600,  # 1 hour TTL
                state_json
            )
            
            # 2. Write-through to PostgreSQL (persistence)
            await self._persist_agent_state_to_db(session_id, state)
            
            save_time = time.time() - start_time
            logger.debug(f"✅ Agent state saved in {save_time:.3f}s (Redis + PostgreSQL)")
            return True
        except Exception as e:
            save_time = time.time() - start_time
            logger.error(f"Error saving agent state after {save_time:.3f}s: {e}")
            # Don't return False, raise the error to prevent fallback
            raise e
    
    async def get_agent_state(self, session_id: str) -> Optional[AgentState]:
        """Get agent state from Redis with fallback to PostgreSQL"""
        start_time = time.time()
        logger.debug(f"📥 Getting agent state for session {session_id}...")
        
        try:
            # 1. Try Redis first (fast access)
            await self.connect()
            state_json = await self.redis_client.get(f"agent_state:{session_id}")
            
            if state_json:
                try:
                    state_dict = json.loads(state_json)
                    state = AgentState.from_dict(state_dict)
                    get_time = time.time() - start_time
                    logger.debug(f"✅ Agent state retrieved from Redis in {get_time:.3f}s")
                    return state
                except Exception as e:
                    logger.error(f"Failed to parse Redis state: {e}")
                    # Don't continue to fallback, raise the error to prevent fallback
                    raise e
            
            # 2. Fallback to PostgreSQL (persistence)
            logger.debug("📥 Redis miss, trying PostgreSQL...")
            state = await self._load_agent_state_from_db(session_id)
            
            if state:
                # Cache in Redis for future access
                try:
                    state_dict = state.to_dict()
                    state_json = json.dumps(state_dict, default=str)
                    await self.redis_client.setex(
                        f"agent_state:{session_id}",
                        3600,  # 1 hour TTL
                        state_json
                    )
                except Exception as e:
                    logger.error(f"Failed to cache state in Redis: {e}")
                    # Don't continue, raise the error to prevent fallback
                    raise e
                
                get_time = time.time() - start_time
                logger.debug(f"✅ Agent state retrieved from PostgreSQL in {get_time:.3f}s")
                return state
            
            get_time = time.time() - start_time
            logger.debug(f"❌ Agent state not found in {get_time:.3f}s")
            # Don't return None, raise the error to prevent fallback
            raise ValueError(f"Agent state not found for session {session_id}")
            
        except Exception as e:
            get_time = time.time() - start_time
            logger.error(f"Error getting agent state after {get_time:.3f}s: {e}")
            # Don't return None, raise the error to prevent fallback
            raise e

    def get_agent_state_for_tools(self, session_id: str) -> Optional[AgentState]:
        """Get agent state for use in synchronous tools"""
        import redis
        import json
        
        try:
            # Create a synchronous Redis client
            sync_redis_client = redis.from_url(self.redis_url, decode_responses=True)
            
            # Get state from Redis
            state_json = sync_redis_client.get(f"agent_state:{session_id}")
            
            if state_json:
                try:
                    state_dict = json.loads(state_json)
                    state = AgentState.from_dict(state_dict)
                    logger.debug(f"✅ Agent state retrieved from Redis for tools")
                    return state
                except Exception as e:
                    logger.error(f"Failed to parse Redis state: {e}")
                    raise e
            
            # If not in Redis, try database (this would need a sync database service)
            logger.debug("📥 Redis miss, trying database...")
            # For now, return None if not in Redis
            # TODO: Implement sync database fallback
            return None
                
        except Exception as e:
            logger.error(f"Error retrieving agent state for tools: {e}")
            raise e

    def save_agent_state_for_tools(self, session_id: str, state: AgentState) -> bool:
        """Save agent state for use in synchronous tools"""
        import redis
        import json
        
        try:
            # Create a synchronous Redis client
            sync_redis_client = redis.from_url(self.redis_url, decode_responses=True)
            
            # Save state to Redis
            state_dict = state.to_dict()
            state_json = json.dumps(state_dict, default=str)
            sync_redis_client.setex(
                f"agent_state:{session_id}",
                3600,  # 1 hour TTL
                state_json
            )
            
            logger.debug(f"✅ Agent state saved to Redis for tools")
            return True
                
        except Exception as e:
            logger.error(f"Error saving agent state for tools: {e}")
            raise e
    
    async def delete_agent_state(self, session_id: str) -> bool:
        """Delete agent state from Redis"""
        try:
            await self.connect()
            await self.redis_client.delete(f"agent_state:{session_id}")
            return True
        except Exception as e:
            logger.error(f"Error deleting agent state: {e}")
            # Don't return False, raise the error to prevent fallback
            raise e
    
    async def _persist_agent_state_to_db(self, session_id: str, state: AgentState):
        """Persist agent state to PostgreSQL"""
        try:
            # Update session metadata
            session_controller = await self.db_service.session_controller
            session = await session_controller.get_session(session_id)
            if not session:
                await session_controller.create_session(
                    session_id=session_id,
                    metadata={"created_at": state.created_at.isoformat()}
                )
            await session_controller.update_session(
                session_id=session_id,
                conversation_status=state.status.value,
                message_count=len(state.messages),
                last_message_at=state.updated_at,
                meta_data={"last_update": state.updated_at.isoformat()}
            )
            
            # Persist messages
            message_controller = await self.db_service.message_controller
            existing_messages = await message_controller.get_messages_by_session(session_id)
            existing_count = len(existing_messages)
            for i, msg in enumerate(state.messages[existing_count:], start=existing_count + 1):
                await message_controller.add_message(
                    session_id=session_id,
                    role=msg.role.value,
                    content=msg.content,
                    metadata=msg.metadata
                )
        except Exception as e:
            logger.error(f"Error persisting agent state to database: {e}")
            raise e
    
    async def _load_agent_state_from_db(self, session_id: str) -> Optional[AgentState]:
        """Load agent state from PostgreSQL"""
        try:
            session_controller = await self.db_service.session_controller
            session = await session_controller.get_session(session_id)
            if not session:
                raise ValueError(f"Session {session_id} not found in database")
            
            message_controller = await self.db_service.message_controller
            messages = await message_controller.get_messages_by_session(session_id)
            from ..db import AgentState, Message, MessageRole, AgentStatus
            agent_messages = []
            for msg in messages:
                agent_messages.append(Message(
                    role=MessageRole(msg.role),
                    content=msg.content,
                    timestamp=msg.timestamp,
                    metadata=msg.message_metadata
                ))
            # Handle None or invalid conversation_status
            try:
                status = AgentStatus(session.conversation_status) if session.conversation_status else AgentStatus.IDLE
            except ValueError:
                # If the status is not a valid enum value, default to IDLE
                logger.warning(f"Invalid conversation_status '{session.conversation_status}' for session {session_id}, defaulting to IDLE")
                status = AgentStatus.IDLE
            
            return AgentState(
                session_id=session_id,
                messages=agent_messages,
                context={},
                status=status,
                created_at=session.created_at,
                updated_at=session.updated_at
            )
        except Exception as e:
            logger.error(f"Error loading agent state from database: {e}")
            raise e
    
    async def list_active_sessions(self) -> List[str]:
        """List all active agent sessions"""
        try:
            await self.connect()
            keys = await self.redis_client.keys("agent_state:*")
            return [key.replace("agent_state:", "") for key in keys]
        except Exception as e:
            logger.error(f"Error listing sessions: {e}")
            # Don't return empty list, raise the error to prevent fallback
            raise e

 