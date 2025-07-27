"""
Database Configuration - Connection setup and engine management
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from ..config.config import config
from render_relay.utils.get_logger import get_logger

logger = get_logger("database_config")

# Database URLs
DATABASE_URL = f"postgresql+asyncpg://{config.POSTGRES_USER}:{config.POSTGRES_PASSWORD}@{config.POSTGRES_HOST}:{config.POSTGRES_PORT}/{config.POSTGRES_DB}"
SYNC_DATABASE_URL = f"postgresql://{config.POSTGRES_USER}:{config.POSTGRES_PASSWORD}@{config.POSTGRES_HOST}:{config.POSTGRES_PORT}/{config.POSTGRES_DB}"

# Async engine for PostgreSQL with improved connection pooling
async_engine = create_async_engine(
    DATABASE_URL,
    echo=False,  # Set to True for SQL debugging
    pool_pre_ping=True,
    pool_recycle=300,
    pool_size=20,  # Increased pool size for better concurrency
    max_overflow=30,  # Allow more connections during peak usage
    pool_timeout=30,  # Timeout for getting connection from pool
    pool_reset_on_return='commit',  # Reset connection state on return
    # Connection isolation settings for better streaming support
    isolation_level='READ_COMMITTED',
    # Asyncpg specific settings
    connect_args={
        "server_settings": {
            "application_name": "agent_with_context",
            "tcp_keepalives_idle": "600",
            "tcp_keepalives_interval": "30",
            "tcp_keepalives_count": "3",
        }
    }
)

# Sync engine for migrations
sync_engine = create_engine(
    SYNC_DATABASE_URL,
    echo=False,
    pool_pre_ping=True,
    pool_recycle=300,
    pool_size=10,
    max_overflow=20,
    pool_timeout=30,
    pool_reset_on_return='commit',
)

# Session factories
AsyncSessionLocal = sessionmaker(
    async_engine, 
    class_=AsyncSession, 
    expire_on_commit=False,
    autocommit=False,
    autoflush=False
)

SyncSessionLocal = sessionmaker(
    sync_engine,
    expire_on_commit=False
) 