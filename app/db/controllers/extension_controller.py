"""
Extension Controller for managing PostgreSQL extension operations
"""

from typing import List, Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, text
from render_relay.utils.get_logger import get_logger

from ..models.extensions import ExtensionManager
from ..config import async_engine

logger = get_logger(__name__)


class ExtensionController:
    """Controller for managing PostgreSQL extension operations"""
    
    def __init__(self):
        """Initialize the controller - manages its own sessions"""
        self.logger = logger
        self.extension_manager = ExtensionManager(async_engine)
    
    async def _get_session(self) -> AsyncSession:
        """Get a database session"""
        from ..config import AsyncSessionLocal
        async with AsyncSessionLocal() as session:
            return session
    
    async def check_extension_exists(self, extension_name: str) -> bool:
        """Check if a PostgreSQL extension exists"""
        try:
            return await self.extension_manager.extension_exists(extension_name)
        except Exception as e:
            self.logger.error(f"Failed to check extension {extension_name}: {e}")
            raise
    
    async def create_extension(self, extension_name: str) -> bool:
        """Create a PostgreSQL extension"""
        try:
            return await self.extension_manager.create_extension(extension_name)
        except Exception as e:
            self.logger.error(f"Failed to create extension {extension_name}: {e}")
            raise
    
    async def ensure_extension(self, extension_name: str) -> bool:
        """Ensure an extension exists, create if it doesn't"""
        try:
            return await self.extension_manager.ensure_extension(extension_name)
        except Exception as e:
            self.logger.error(f"Failed to ensure extension {extension_name}: {e}")
            raise
    
    async def list_extensions(self) -> List[Dict[str, Any]]:
        """List all installed PostgreSQL extensions"""
        try:
            db = await self._get_session()
            try:
                stmt = text("""
                    SELECT extname, extversion, extowner, extnamespace
                    FROM pg_extension
                    ORDER BY extname
                """)
                result = await db.execute(stmt)
                
                extensions = []
                for row in result:
                    extensions.append({
                        "name": row.extname,
                        "version": row.extversion,
                        "owner": row.extowner,
                        "namespace": row.extnamespace
                    })
                
                return extensions
            finally:
                await db.close()
                
        except Exception as e:
            self.logger.error(f"Failed to list extensions: {e}")
            raise
    
    async def drop_extension(self, extension_name: str, cascade: bool = False) -> bool:
        """Drop a PostgreSQL extension"""
        try:
            db = await self._get_session()
            try:
                # Check if extension exists
                if not await self.check_extension_exists(extension_name):
                    self.logger.info(f"Extension {extension_name} does not exist")
                    return True
                
                # Drop extension
                cascade_clause = " CASCADE" if cascade else ""
                stmt = text(f"DROP EXTENSION {extension_name}{cascade_clause}")
                await db.execute(stmt)
                await db.commit()
                
                self.logger.info(f"Extension {extension_name} dropped successfully")
                return True
            finally:
                await db.close()
                
        except Exception as e:
            self.logger.error(f"Failed to drop extension {extension_name}: {e}")
            raise
    
    async def get_extension_info(self, extension_name: str) -> Optional[Dict[str, Any]]:
        """Get detailed information about a specific extension"""
        try:
            db = await self._get_session()
            try:
                stmt = text("""
                    SELECT extname, extversion, extowner, extnamespace, extrelocatable
                    FROM pg_extension
                    WHERE extname = :extname
                """)
                result = await db.execute(stmt, {"extname": extension_name})
                row = result.fetchone()
                
                if row:
                    return {
                        "name": row.extname,
                        "version": row.extversion,
                        "owner": row.extowner,
                        "namespace": row.extnamespace,
                        "relocatable": row.extrelocatable
                    }
                return None
            finally:
                await db.close()
                
        except Exception as e:
            self.logger.error(f"Failed to get extension info for {extension_name}: {e}")
            raise 