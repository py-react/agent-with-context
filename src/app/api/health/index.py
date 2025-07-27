from fastapi import Request
from app.factory.service_factory import service_factory
from langchain_core.messages import HumanMessage

async def GET(request: Request):
    """Health check endpoint to verify all services"""
    health_status = {
        "status": "healthy",
        "services": {},
        "config": {},
        "models": {}
    }
    
    try:
        # Get services and config directly from service factory
        config = service_factory.get_config()
        
        # Check configuration
        config_valid = config.validate()
        health_status["config"] = {
            "valid": config_valid,
            "redis_url": config.REDIS_URL,
            "max_context_length": config.MAX_CONTEXT_LENGTH,
            "agent_state_ttl": config.AGENT_STATE_TTL,
            "max_context_chunks": config.MAX_CONTEXT_CHUNKS,
            "context_chunk_size": config.CONTEXT_CHUNK_SIZE,
            "context_chunk_overlap": config.CONTEXT_CHUNK_OVERLAP
        }
        
        # Enhanced model information
        health_status["models"] = {
            "llm": {
                "provider": "Google Gemini",
                "model": config.GEMINI_MODEL,
                "temperature": config.GEMINI_TEMPERATURE,
                "api_key_configured": bool(config.GEMINI_API_KEY)
            },
            "embedding": {
                "provider": "Google Gemini",
                "model": config.EMBEDDING_MODEL,
                "api_key_configured": bool(config.GEMINI_API_KEY)
            }
        }
        
        # Check Redis
        try:
            # Get Redis service directly from service factory
            redis_service = service_factory.get_service('redis')
            
            redis_connected = await redis_service.test_connection()
            health_status["services"]["redis"] = {
                "status": "healthy" if redis_connected else "unhealthy",
                "connected": redis_connected
            }
        except Exception as e:
            health_status["services"]["redis"] = {
                "status": "error",
                "error": str(e)
            }
        
        # Check LLM Connection (basic test)
        try:
            # Get LLM directly from service factory
            llm = service_factory.get_llm()
            
            # Simple test message to check LLM connectivity
            response = await llm.ainvoke([HumanMessage(content="Hello, health check test.")])
            response_content = response.content if response.content else ""
            
            health_status["services"]["llm"] = {
                "status": "healthy",
                "model": config.GEMINI_MODEL,
                "response_length": len(response_content),
                "test_successful": True,
                "provider": "Google Gemini"
            }
        except Exception as e:
            health_status["services"]["llm"] = {
                "status": "error",
                "error": str(e),
                "test_successful": False
            }
        
        # Check Database Connection
        try:
            db_service = service_factory.get_service('db')
            
            # Check if database service is initialized
            if not hasattr(db_service, '_initialized') or not db_service._initialized:
                # Try to initialize the database service
                try:
                    await db_service.initialize()
                except Exception as init_error:
                    health_status["services"]["database"] = {
                        "status": "error",
                        "error": f"Database initialization failed: {str(init_error)}",
                        "type": "PostgreSQL + pgvector",
                        "initialized": False
                    }
                    raise init_error
            
            # Test the connection
            try:
                db_connected = await db_service.test_connection()
                health_status["services"]["database"] = {
                    "status": "healthy" if db_connected else "unhealthy",
                    "connected": db_connected,
                    "type": "PostgreSQL + pgvector",
                    "initialized": True
                }
            except Exception as test_error:
                health_status["services"]["database"] = {
                    "status": "error",
                    "error": f"Connection test failed: {str(test_error)}",
                    "type": "PostgreSQL + pgvector",
                    "initialized": True,
                    "connected": False
                }
        except Exception as e:
            health_status["services"]["database"] = {
                "status": "error",
                "error": str(e),
                "type": "PostgreSQL + pgvector",
                "initialized": getattr(db_service, '_initialized', False) if 'db_service' in locals() else False
            }
        
        # Overall status
        all_healthy = all(
            service.get("status") == "healthy" 
            for service in health_status["services"].values()
        )
        
        if not all_healthy:
            health_status["status"] = "unhealthy"
        
        return health_status
        
    except Exception as e:
        return {
            "status": "error",
            "message": f"Health check failed: {str(e)}"
        } 