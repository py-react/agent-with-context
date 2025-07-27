"""
Database Layer - Configuration and models

This module provides database configuration and models.
Session management and initialization are now handled by DatabaseService.
"""

# Import configuration
from .config import (
    async_engine,
    sync_engine,
    AsyncSessionLocal,
    SyncSessionLocal,
    DATABASE_URL,
    SYNC_DATABASE_URL
)

# Import models
from .models import Base, ContextEmbedding, ConversationMessage, Session

# Re-export everything for backward compatibility
__all__ = [
    # Configuration
    'async_engine',
    'sync_engine', 
    'AsyncSessionLocal',
    'SyncSessionLocal',
    'DATABASE_URL',
    'SYNC_DATABASE_URL',
    
    # Models
    'Base',
    'ContextEmbedding',
    'ConversationMessage', 
    'Session'
] 