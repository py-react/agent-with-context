class ExtensionManager:
    """Manager for PostgreSQL extensions using SQLAlchemy"""
    
    def __init__(self, engine):
        self.engine = engine
    
    async def extension_exists(self, extension_name: str) -> bool:
        """Check if a PostgreSQL extension exists"""
        try:
            from sqlalchemy import select, text
            from sqlalchemy.ext.asyncio import AsyncSession
            
            async with AsyncSession(self.engine) as session:
                # Use a more SQLAlchemy-friendly approach
                result = await session.execute(
                    select(text("1")).where(
                        text("EXISTS (SELECT 1 FROM pg_extension WHERE extname = :extname)")
                    ).params(extname=extension_name)
                )
                return result.scalar() is not None
        except Exception as e:
            print(f"Error checking extension {extension_name}: {e}")
            return False
    
    async def create_extension(self, extension_name: str) -> bool:
        """Create a PostgreSQL extension"""
        try:
            from sqlalchemy import DDL
            from sqlalchemy.ext.asyncio import AsyncSession
            
            async with AsyncSession(self.engine) as session:
                # Check if extension already exists
                if await self.extension_exists(extension_name):
                    print(f"Extension {extension_name} already exists")
                    return True
                
                # Create extension using DDL
                create_stmt = DDL(f"CREATE EXTENSION {extension_name}")
                await session.execute(create_stmt)
                await session.commit()
                print(f"Extension {extension_name} created successfully")
                return True
                
        except Exception as e:
            print(f"Error creating extension {extension_name}: {e}")
            return False
    
    async def ensure_extension(self, extension_name: str) -> bool:
        """Ensure an extension exists, create if it doesn't"""
        if await self.extension_exists(extension_name):
            return True
        return await self.create_extension(extension_name) 