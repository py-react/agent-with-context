"""
Database Initialization Manager - Database setup and extension management
"""

from .config import async_engine
from .models.extensions import ExtensionManager
from render_relay.utils.get_logger import get_logger

logger = get_logger("init_manager")

async def init_db():
    """Initialize database tables and extensions"""
    try:
        # Initialize extension manager
        extension_manager = ExtensionManager(async_engine)
        
        # Ensure pgvector extension exists
        vector_extension_success = await extension_manager.ensure_extension('vector')
        if vector_extension_success:
            logger.info("pgvector extension ensured successfully")
        else:
            logger.warning("Could not ensure pgvector extension - vector operations may not work")
        
        # Note: Don't create tables here - let Alembic handle migrations
        # The tables will be created by running: alembic upgrade head
        logger.info("Database extensions initialized successfully")
        logger.info("Run 'alembic upgrade head' to apply database migrations")
            
    except Exception as e:
        logger.error(f"Error initializing database: {e}")
        raise e 