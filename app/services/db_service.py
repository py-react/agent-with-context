"""
Database Service for managing database operations and connections.

This service uses the /db package to interact with the database through
SQLAlchemy ORM models and business logic controllers.
"""

from typing import Dict, Any, List, Optional
import asyncio
from sqlalchemy.ext.asyncio import AsyncSession
from render_relay.utils.get_logger import get_logger

# Import from our /db package - only configuration and models
from ..db.config import AsyncSessionLocal, async_engine
from ..db.models import (
    ContextEmbedding,
    ConversationMessage,
    Session
)

logger = get_logger(__name__)


class DatabaseService:
    """Service for managing database operations using /db package."""
    
    def __init__(self):
        """Initialize the database service."""
        self.logger = logger
        self._initialized = False
    
    async def _ensure_vector_extension(self):
        """Internal function to ensure vector extension exists"""
        try:
            # Import here to avoid circular imports
            from ..db.controllers.extension_controller import ExtensionController
            
            # Initialize extension controller
            extension_controller = ExtensionController()
            
            # Ensure pgvector extension exists
            vector_extension_success = await extension_controller.ensure_extension('vector')
            if vector_extension_success:
                self.logger.info("pgvector extension ensured successfully")
            else:
                self.logger.warning("Could not ensure pgvector extension - vector operations may not work")
            
            return vector_extension_success
        except Exception as e:
            self.logger.error(f"Error ensuring vector extension: {e}")
            return False
    
    async def initialize(self):
        """Initialize database connection and extensions."""
        try:
            # Ensure vector extension
            await self._ensure_vector_extension()
            
            # Note: Don't create tables here - let Alembic handle migrations
            # The tables will be created by running: alembic upgrade head
            self.logger.info("Database extensions initialized successfully")
            self.logger.info("Run 'alembic upgrade head' to apply database migrations")
            
            self._initialized = True
            self.logger.info("Database service initialized successfully")
        except Exception as e:
            self.logger.error(f"Failed to initialize database service: {e}")
            raise
    
    async def get_session(self) -> AsyncSession:
        """Get a database session with proper error handling"""
        if not self._initialized:
            await self.initialize()
        
        try:
            async with AsyncSessionLocal() as session:
                return session
        except Exception as e:
            self.logger.error(f"Error creating database session: {e}")
            raise e

    @property
    async def context_controller(self) -> 'ContextController':
        """Get context controller - controller manages its own session"""
        from ..db.controllers.context_controller import ContextController
        return ContextController()

    @property
    async def session_controller(self) -> 'SessionController':
        """Get session controller - controller manages its own session"""
        from ..db.controllers.session_controller import SessionController
        return SessionController()

    @property
    async def message_controller(self) -> 'MessageController':
        """Get message controller - controller manages its own session"""
        from ..db.controllers.message_controller import MessageController
        return MessageController()

    @property
    async def agent_state_controller(self) -> 'AgentStateController':
        # AgentStateController doesn't need a session, it's stateless
        from ..db.controllers.agent_state_controller import AgentStateController
        return AgentStateController()

    @property
    async def workflow_state_controller(self) -> 'WorkflowStateController':
        # WorkflowStateController doesn't need a session, it's stateless
        from ..db.controllers.workflow_state_controller import WorkflowStateController
        return WorkflowStateController()

    @property
    async def extension_controller(self) -> 'ExtensionController':
        """Get extension controller - controller manages its own session"""
        from ..db.controllers.extension_controller import ExtensionController
        return ExtensionController()

    async def close(self):
        """Close database connections."""
        try:
            await async_engine.dispose()
            self.logger.info("Database connections closed successfully")
        except Exception as e:
            self.logger.error(f"Error closing database connections: {e}")
    
    async def ensure_vector_extension(self) -> bool:
        """Public function to ensure vector extension - can be used by service layer"""
        return await self._ensure_vector_extension()
    
    async def list_extensions(self) -> List[Dict[str, Any]]:
        """List all PostgreSQL extensions through service layer"""
        try:
            extension_controller = await self.extension_controller
            return await extension_controller.list_extensions()
        except Exception as e:
            self.logger.error(f"Failed to list extensions: {e}")
            return []
    
    async def test_connection(self) -> bool:
        """Test database connection by attempting to create a session and execute a simple query"""
        try:
            async with AsyncSessionLocal() as session:
                from sqlalchemy import text
                result = await session.execute(text("SELECT 1"))
                result.scalar()
                self.logger.info("Database connection test successful")
                return True
        except Exception as e:
            self.logger.error(f"Database connection test failed: {e}")
            return False 