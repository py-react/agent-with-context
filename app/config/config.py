import os
from typing import Optional
from render_relay.utils.get_logger import get_logger

from dotenv import load_dotenv

load_dotenv()

logger = get_logger("config")

class Config:
    """Configuration management for the agent system"""
    
    # Redis Configuration
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379")
    
    # PostgreSQL + pgvector Configuration
    POSTGRES_HOST: str = os.getenv("POSTGRES_HOST", "localhost")
    POSTGRES_PORT: int = int(os.getenv("POSTGRES_PORT", "5432"))
    POSTGRES_USER: str = os.getenv("POSTGRES_USER", "agent_user")
    POSTGRES_PASSWORD: str = os.getenv("POSTGRES_PASSWORD", "agent_password")
    POSTGRES_DB: str = os.getenv("POSTGRES_DB", "agent_context")
    
    # Gemini Configuration
    GEMINI_API_KEY: Optional[str] = os.getenv("GEMINI_API_KEY")
    GEMINI_MODEL: str = os.getenv("GEMINI_MODEL", "gemini-2.5-flash-lite")
    GEMINI_TEMPERATURE: float = float(os.getenv("GEMINI_TEMPERATURE", "0.7"))
    
    # Agent Configuration
    MAX_CONTEXT_LENGTH: int = int(os.getenv("MAX_CONTEXT_LENGTH", "2048"))
    AGENT_STATE_TTL: int = int(os.getenv("AGENT_STATE_TTL", "3600"))  # 1 hour
    
    # Vector Database Configuration
    EMBEDDING_MODEL: str = os.getenv("EMBEDDING_MODEL", "models/embedding-001")
    MAX_CONTEXT_CHUNKS: int = int(os.getenv("MAX_CONTEXT_CHUNKS", "250"))
    CONTEXT_CHUNK_SIZE: int = int(os.getenv("CONTEXT_CHUNK_SIZE", "1000"))
    CONTEXT_CHUNK_OVERLAP: int = int(os.getenv("CONTEXT_CHUNK_OVERLAP", "200"))
    
    # Limits Configuration - Single Source of Truth for all limits
    # Message History Limits
    DEFAULT_MESSAGE_LIMIT: int = int(os.getenv("DEFAULT_MESSAGE_LIMIT", "250"))
    MAX_MESSAGE_LIMIT: int = int(os.getenv("MAX_MESSAGE_LIMIT", "500"))
    
    # Context Limits
    DEFAULT_CONTEXT_LIMIT: int = int(os.getenv("DEFAULT_CONTEXT_LIMIT", "250"))
    MAX_CONTEXT_LIMIT: int = int(os.getenv("MAX_CONTEXT_LIMIT", "5000"))
    CONTEXT_SEARCH_LIMIT: int = int(os.getenv("CONTEXT_SEARCH_LIMIT", "1000"))
    CONTEXT_SIMILARITY_THRESHOLD: float = float(os.getenv("CONTEXT_SIMILARITY_THRESHOLD", "0.1"))
    
    # Session Limits
    SESSION_MESSAGE_LIMIT: int = int(os.getenv("SESSION_MESSAGE_LIMIT", "100"))
    
    # Tool Limits
    TOOL_DEFAULT_LIMIT: int = int(os.getenv("TOOL_DEFAULT_LIMIT", "250"))
    TOOL_MAX_LIMIT: int = int(os.getenv("TOOL_MAX_LIMIT", "500"))
    
    # Search Limits
    DEFAULT_SEARCH_LIMIT: int = int(os.getenv("DEFAULT_SEARCH_LIMIT", "10"))
    
    @classmethod
    def validate(cls) -> bool:
        """Validate that required configuration is present"""
        if not cls.GEMINI_API_KEY:
            logger.error("GEMINI_API_KEY environment variable is required")
            return False
        
        logger.info("Configuration validated successfully")
        return True
    
    @classmethod
    def print_config(cls):
        """Print current configuration (without sensitive data)"""
        logger.info("Agent Configuration:")
        logger.info(f"  Redis URL: {cls.REDIS_URL}")
        logger.info(f"  PostgreSQL Host: {cls.POSTGRES_HOST}:{cls.POSTGRES_PORT}")
        logger.info(f"  PostgreSQL Database: {cls.POSTGRES_DB}")
        logger.info(f"  Gemini Model: {cls.GEMINI_MODEL}")
        logger.info(f"  Gemini Temperature: {cls.GEMINI_TEMPERATURE}")
        logger.info(f"  Max Context Length: {cls.MAX_CONTEXT_LENGTH}")
        logger.info(f"  Agent State TTL: {cls.AGENT_STATE_TTL} seconds")
        logger.info(f"  Embedding Model: {cls.EMBEDDING_MODEL}")
        logger.info(f"  Context Chunk Size: {cls.CONTEXT_CHUNK_SIZE}")
        logger.info(f"  Gemini API Key: {'Set' if cls.GEMINI_API_KEY else 'Missing'}")
        
        # Print limits configuration
        logger.info("Limits Configuration:")
        logger.info(f"  Default Message Limit: {cls.DEFAULT_MESSAGE_LIMIT}")
        logger.info(f"  Max Message Limit: {cls.MAX_MESSAGE_LIMIT}")
        logger.info(f"  Default Context Limit: {cls.DEFAULT_CONTEXT_LIMIT}")
        logger.info(f"  Max Context Limit: {cls.MAX_CONTEXT_LIMIT}")
        logger.info(f"  Context Search Limit: {cls.CONTEXT_SEARCH_LIMIT}")
        logger.info(f"  Context Similarity Threshold: {cls.CONTEXT_SIMILARITY_THRESHOLD}")
        logger.info(f"  Session Message Limit: {cls.SESSION_MESSAGE_LIMIT}")
        logger.info(f"  Tool Default Limit: {cls.TOOL_DEFAULT_LIMIT}")
        logger.info(f"  Tool Max Limit: {cls.TOOL_MAX_LIMIT}")
        logger.info(f"  Default Search Limit: {cls.DEFAULT_SEARCH_LIMIT}")

# Global config instance
config = Config() 