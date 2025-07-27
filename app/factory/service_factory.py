"""
Service Factory for creating and managing service dependencies
"""

import time
import signal
import asyncio
from typing import List, Dict, Any
from langchain_core.tools import BaseTool
from render_relay.utils.get_logger import get_logger

from ..services.db_service import DatabaseService
from ..services.redis_service import RedisService
from ..services.context_service import ContextService
from ..services.vector_service import VectorService
from ..services.message_history_service import MessageHistoryService
from ..services.agent_service import AgentService
from ..services.langgraph_service import LangGraphService
from ..services.session_service import SessionService
from ..db.models.agent_state import AgentState, MessageRole, AgentStatus
from ..config.config import config
from .llm_factory import LLMFactory
from .workflow_factory import workflow_factory

logger = get_logger("service_factory")

class ServiceFactory:
    """Factory for creating and managing service dependencies"""
    
    def __init__(self):
        self._services = {}
        self._initialized = False
        self._signal_handlers_registered = False
        self._register_signal_handlers()
    
    def _register_signal_handlers(self):
        """Register signal handlers for graceful shutdown (only once)"""
        if not self._signal_handlers_registered:
            signal.signal(signal.SIGINT, self._signal_handler)
            signal.signal(signal.SIGTERM, self._signal_handler)
            self._signal_handlers_registered = True
            logger.debug("Signal handlers registered for graceful shutdown")
    
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals to close all services gracefully"""
        logger.info(f"Received signal {signum}, initiating graceful shutdown...")
        try:
            # Get the current event loop
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # Schedule the cleanup
                loop.create_task(self.cleanup_services())
            else:
                # Run the cleanup directly
                loop.run_until_complete(self.cleanup_services())
        except Exception as e:
            logger.error(f"Error during graceful shutdown: {e}")
    
    def initialize_services(self, tools: List[BaseTool] = None):
        """Initialize all services with proper dependencies"""
        start_time = time.time()
        logger.info("🏭 ServiceFactory.initialize_services started")
        
        if self._initialized:
            logger.debug("✅ Services already initialized, skipping")
            return
        
        # Create base services (no dependencies)
        base_start = time.time()
        logger.debug("🔧 Creating base services...")
        self._services['db'] = DatabaseService()
        self._services['redis'] = RedisService(db_service=self._services['db'])
        base_time = time.time() - base_start
        logger.debug(f"✅ Base services created in {base_time:.3f}s")
        
        # Create services that need database access
        db_start = time.time()
        logger.debug("🔧 Creating services with database dependencies...")
        self._services['context'] = ContextService(db_service=self._services['db'])
        self._services['vector'] = VectorService(db_service=self._services['db'])
        
        # Create message history service
        self._services['message_history'] = MessageHistoryService(
            redis_service=self._services['redis']
        )
        db_time = time.time() - db_start
        logger.debug(f"✅ Database-dependent services created in {db_time:.3f}s")
        
        # Create services that need tools (dependency injection)
        tool_start = time.time()
        logger.debug("🔧 Creating services with tool dependencies...")
        self._services['agent'] = AgentService(tools=tools)
        self._services['langgraph'] = LangGraphService()
        tool_time = time.time() - tool_start
        logger.debug(f"✅ Tool-dependent services created in {tool_time:.3f}s")
        
        # Create unified session service with all dependencies
        session_start = time.time()
        logger.debug("🔧 Creating unified session service...")
        self._services['session'] = SessionService(
            db_service=self._services['db'],
            redis_service=self._services['redis'],
            vector_service=self._services['vector'],
            agent_service=self._services['agent']
        )
        session_time = time.time() - session_start
        logger.debug(f"✅ Unified session service created in {session_time:.3f}s")
        
        self._initialized = True
        total_time = time.time() - start_time
        logger.info(f"🎉 ServiceFactory.initialize_services completed in {total_time:.3f}s (base: {base_time:.3f}s, db: {db_time:.3f}s, tool: {tool_time:.3f}s)")
    
    def update_tools(self, tools: List[BaseTool]):
        """Update tools for services that need them"""
        if 'agent' in self._services:
            self._services['agent'].set_tools(tools)
    
    def get_service(self, service_name: str):
        """Get a service by name"""
        if not self._initialized:
            raise RuntimeError("Services not initialized. Call initialize_services() first.")
        
        if service_name not in self._services:
            raise ValueError(f"Service '{service_name}' not found")
        
        return self._services[service_name]
    
    def get_all_services(self):
        """Get all services"""
        if not self._initialized:
            raise RuntimeError("Services not initialized. Call initialize_services() first.")
        
        return self._services.copy()
    
    def get_models(self):
        """Get database models for API use"""
        return {
            'AgentState': AgentState,
            'MessageRole': MessageRole,
            'AgentStatus': AgentStatus
        }
    
    def get_config(self):
        """Get configuration for API use"""
        return config
    
    def get_llm(self):
        """Get LLM instance for API use"""
        return LLMFactory.get_default_llm()
    
    async def initialize_async_services(self):
        """Initialize async services (like Redis connection and database)"""
        start_time = time.time()
        logger.info("⚡ ServiceFactory.initialize_async_services started")
        
        if 'redis' in self._services:
            redis_start = time.time()
            logger.debug("🔌 Connecting to Redis...")
            await self._services['redis'].connect()
            redis_time = time.time() - redis_start
            logger.debug(f"✅ Redis connection established in {redis_time:.3f}s")
        
        if 'db' in self._services:
            db_start = time.time()
            logger.debug("🗄️ Initializing database service...")
            await self._services['db'].initialize()
            db_time = time.time() - db_start
            logger.debug(f"✅ Database service initialized in {db_time:.3f}s")
        
        total_time = time.time() - start_time
        logger.info(f"🎉 ServiceFactory.initialize_async_services completed in {total_time:.3f}s")
    
    def get_workflow_factory(self):
        """Get the workflow factory instance"""
        workflow_factory.set_service_factory(self)
        return workflow_factory
    
    async def cleanup_services(self):
        """Centralized cleanup for all services (close connections, etc.)"""
        start_time = time.time()
        logger.info("🧹 ServiceFactory.cleanup_services started")
        
        cleanup_errors = []
        
        # Cleanup Redis service
        if 'redis' in self._services:
            try:
                redis_start = time.time()
                logger.debug("🔌 Disconnecting from Redis...")
                await self._services['redis'].disconnect()
                redis_time = time.time() - redis_start
                logger.debug(f"✅ Redis disconnected in {redis_time:.3f}s")
            except Exception as e:
                error_msg = f"Failed to disconnect Redis: {e}"
                logger.error(error_msg)
                cleanup_errors.append(error_msg)
        
        # Cleanup Database service
        if 'db' in self._services:
            try:
                db_start = time.time()
                logger.debug("🗄️ Closing database connections...")
                await self._services['db'].close()
                db_time = time.time() - db_start
                logger.debug(f"✅ Database connections closed in {db_time:.3f}s")
            except Exception as e:
                error_msg = f"Failed to close database connections: {e}"
                logger.error(error_msg)
                cleanup_errors.append(error_msg)
        
        # Clear services dictionary
        self._services.clear()
        self._initialized = False
        
        total_time = time.time() - start_time
        if cleanup_errors:
            logger.error(f"❌ ServiceFactory.cleanup_services completed with errors in {total_time:.3f}s")
            for error in cleanup_errors:
                logger.error(f"  - {error}")
        else:
            logger.info(f"🎉 ServiceFactory.cleanup_services completed successfully in {total_time:.3f}s")

# Global service factory instance
service_factory = ServiceFactory() 