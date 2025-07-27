"""
Database package for agent_with_context

This package provides:
- SQLAlchemy ORM models in /models/
- Business logic controllers in /controllers/
- Database configuration and connections

Note: Session management and initialization are now handled by the DatabaseService
in the services layer to maintain proper layering.
"""

# Database configuration and connections
from .config import (
    async_engine,
    sync_engine,
    AsyncSessionLocal,
    SyncSessionLocal,
    DATABASE_URL,
    SYNC_DATABASE_URL
)

# SQLAlchemy ORM Models
from .models import Base, ContextEmbedding, ConversationMessage, Session
from .models.agent_state import AgentState, Message, MessageRole, AgentStatus
from .models.workflow_state import WorkflowState, WorkflowStep
from .models.extensions import ExtensionManager

# Business Logic Controllers (imported by service layer only)
# Note: Sync controllers are exported for sync operations in tools
from .controllers.context_controller import ContextControllerSync
from .controllers.message_controller import MessageControllerSync

__all__ = [
    # Database configuration and connections
    'async_engine',
    'sync_engine', 
    'AsyncSessionLocal',
    'SyncSessionLocal',
    'DATABASE_URL',
    'SYNC_DATABASE_URL',
    
    # SQLAlchemy ORM Models
    'Base',
    'ContextEmbedding',
    'ConversationMessage', 
    'Session',
    'AgentState', 
    'Message',
    'MessageRole',
    'AgentStatus',
    'WorkflowState',
    'WorkflowStep',
    'ExtensionManager',
    
    # Sync Controllers (for tools and sync operations)
    'ContextControllerSync',
    'MessageControllerSync'
] 