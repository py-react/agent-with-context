from fastapi import FastAPI
from app.initialize import initialize_application, cleanup_application
from render_relay.utils.get_logger import get_logger
import asyncio


async def startup(app:FastAPI):
    startLogger = get_logger("My AppLifespan: Start")
    
    # Initialize the application with proper service dependencies
    try:
        await initialize_application()
        startLogger.info("Application services initialized successfully")
    except Exception as e:
        startLogger.error(f"Failed to initialize application services: {e}")
        raise e
    
    startLogger.info("🚀 Application startup completed successfully")

async def shutdown(app:FastAPI):
    stopLogger = get_logger("My AppLifespan: Cleanup")
    
    # Cleanup application services (handles all cleanup including database and Redis)
    try:
        await cleanup_application()
        stopLogger.info("Application services cleaned up successfully")
    except Exception as e:
        stopLogger.error(f"Error cleaning up application services: {e}")
    
    stopLogger.info("🛑 Application shutdown completed")

def extend_app(app:FastAPI):
    extend_app_logger = get_logger("Extend App: ")
    extend_app_logger.info("Extending App")
