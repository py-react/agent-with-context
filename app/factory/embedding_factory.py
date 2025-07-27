"""
Embedding Factory for creating model-agnostic embedding models using LangChain
"""

from typing import List, Optional
from render_relay.utils.get_logger import get_logger
from ..config.config import config

logger = get_logger("embedding_factory")

class EmbeddingFactory:
    """Factory for creating embedding models from different providers using LangChain"""
    
    @staticmethod
    def create_embedding_model(provider: str = "auto", **kwargs) -> Optional[object]:
        """
        Create an embedding model based on the provider using LangChain
        
        Args:
            provider: Model provider ("gemini", "openai", "auto")
            **kwargs: Additional arguments for the model
        
        Returns:
            LangChain embedding model instance
        """
        try:
            if provider == "auto":
                # Try to detect available providers
                if config.GEMINI_API_KEY:
                    provider = "gemini"
                else:
                    logger.warning("No embedding provider configured")
                    return None
            
            if provider == "gemini":
                return EmbeddingFactory._create_gemini_embedding(**kwargs)
            elif provider == "openai":
                return EmbeddingFactory._create_openai_embedding(**kwargs)
            else:
                logger.error(f"Unsupported embedding provider: {provider}")
                return None
                
        except Exception as e:
            logger.error(f"Error creating embedding model: {e}")
            return None
    
    @staticmethod
    def _create_gemini_embedding(**kwargs) -> Optional[object]:
        """Create a Gemini embedding model using LangChain's Google GenAI integration"""
        try:
            from langchain_google_genai import GoogleGenerativeAIEmbeddings
            
            if not config.GEMINI_API_KEY:
                logger.error("GEMINI_API_KEY not configured")
                return None
            
            model_name = kwargs.get("model", config.EMBEDDING_MODEL)
            
            return GoogleGenerativeAIEmbeddings(
                model=model_name,
                google_api_key=config.GEMINI_API_KEY
            )
            
        except ImportError:
            logger.error("langchain-google-genai not installed. Please install: pip install langchain-google-genai")
            return None
        except Exception as e:
            logger.error(f"Error creating Gemini embedding model: {e}")
            return None
    
    @staticmethod
    def _create_openai_embedding(**kwargs) -> Optional[object]:
        """Create an OpenAI embedding model using LangChain"""
        try:
            from langchain_openai import OpenAIEmbeddings
            
            # You would need to add OpenAI configuration to config.py
            openai_api_key = kwargs.get("api_key") or config.OPENAI_API_KEY if hasattr(config, 'OPENAI_API_KEY') else None
            
            if not openai_api_key:
                logger.error("OpenAI API key not configured")
                return None
            
            model = kwargs.get("model", "text-embedding-ada-002")
            
            return OpenAIEmbeddings(
                model=model,
                openai_api_key=openai_api_key
            )
            
        except ImportError:
            logger.error("langchain-openai not installed")
            return None
        except Exception as e:
            logger.error(f"Error creating OpenAI embedding model: {e}")
            return None
    
    @staticmethod
    def get_embedding(text: str, provider: str = "auto", **kwargs) -> List[float]:
        """
        Get embedding for text using the specified provider via LangChain
        
        Args:
            text: Text to embed
            provider: Model provider ("gemini", "openai", "auto")
            **kwargs: Additional arguments for the model
        
        Returns:
            List of embedding values
        """
        try:
            model = EmbeddingFactory.create_embedding_model(provider, **kwargs)
            
            if not model:
                logger.error("No embedding model available")
                return [0.0] * 768  # Default embedding size
            
            # Use LangChain's embed_query method
            embedding = model.embed_query(text)
            return embedding
                
        except Exception as e:
            logger.error(f"Error getting embedding: {e}")
            return [0.0] * 768
    
    @staticmethod
    def get_embeddings(texts: List[str], provider: str = "auto", **kwargs) -> List[List[float]]:
        """
        Get embeddings for multiple texts using the specified provider via LangChain
        
        Args:
            texts: List of texts to embed
            provider: Model provider ("gemini", "openai", "auto")
            **kwargs: Additional arguments for the model
        
        Returns:
            List of embedding lists
        """
        try:
            model = EmbeddingFactory.create_embedding_model(provider, **kwargs)
            
            if not model:
                logger.error("No embedding model available")
                return [[0.0] * 768] * len(texts)  # Default embeddings
            
            # Use LangChain's embed_documents method
            embeddings = model.embed_documents(texts)
            return embeddings
                
        except Exception as e:
            logger.error(f"Error getting embeddings: {e}")
            return [[0.0] * 768] * len(texts)
    
    @staticmethod
    def get_default_embedding_model() -> Optional[object]:
        """Get the default embedding model based on configuration"""
        return EmbeddingFactory.create_embedding_model("auto")
    
    @staticmethod
    def get_available_providers() -> list:
        """Get list of available embedding providers"""
        providers = []
        
        if config.GEMINI_API_KEY:
            providers.append("gemini")
        
        if hasattr(config, 'OPENAI_API_KEY') and config.OPENAI_API_KEY:
            providers.append("openai")
        
        return providers 