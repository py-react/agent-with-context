"""
LLM Factory for creating model-agnostic language models
"""

from typing import Optional
from langchain_core.language_models import BaseLanguageModel
from render_relay.utils.get_logger import get_logger
from ..config.config import config

logger = get_logger("llm_factory")

class LLMFactory:
    """Factory for creating language models from different providers"""
    
    @staticmethod
    def create_llm(provider: str = "auto", **kwargs) -> Optional[BaseLanguageModel]:
        """
        Create a language model based on the provider
        
        Args:
            provider: Model provider ("gemini", "openai", "auto")
            **kwargs: Additional arguments for the model
        
        Returns:
            LangChain language model instance
        """
        try:
            if provider == "auto":
                # Try to detect available providers
                if config.GEMINI_API_KEY:
                    provider = "gemini"
                else:
                    logger.warning("No LLM provider configured")
                    return None
            
            if provider == "gemini":
                return LLMFactory._create_gemini_llm(**kwargs)
            elif provider == "openai":
                return LLMFactory._create_openai_llm(**kwargs)
            else:
                logger.error(f"Unsupported LLM provider: {provider}")
                return None
                
        except Exception as e:
            logger.error(f"Error creating LLM: {e}")
            return None
    
    @staticmethod
    def _create_gemini_llm(**kwargs) -> Optional[BaseLanguageModel]:
        """Create a Gemini language model"""
        try:
            from langchain_google_genai import ChatGoogleGenerativeAI
            
            if not config.GEMINI_API_KEY:
                logger.error("GEMINI_API_KEY not configured")
                return None
            
            model = kwargs.get("model", config.GEMINI_MODEL)
            temperature = kwargs.get("temperature", config.GEMINI_TEMPERATURE)
            
            return ChatGoogleGenerativeAI(
                model=model,
                temperature=temperature,
                google_api_key=config.GEMINI_API_KEY
            )
            
        except ImportError:
            logger.error("langchain-google-genai not installed")
            return None
        except Exception as e:
            logger.error(f"Error creating Gemini LLM: {e}")
            return None
    
    @staticmethod
    def _create_openai_llm(**kwargs) -> Optional[BaseLanguageModel]:
        """Create an OpenAI language model"""
        try:
            from langchain_openai import ChatOpenAI
            
            # You would need to add OpenAI configuration to config.py
            openai_api_key = kwargs.get("api_key") or config.OPENAI_API_KEY if hasattr(config, 'OPENAI_API_KEY') else None
            
            if not openai_api_key:
                logger.error("OpenAI API key not configured")
                return None
            
            model = kwargs.get("model", "gpt-3.5-turbo")
            temperature = kwargs.get("temperature", 0.7)
            
            return ChatOpenAI(
                model=model,
                temperature=temperature,
                openai_api_key=openai_api_key
            )
            
        except ImportError:
            logger.error("langchain-openai not installed")
            return None
        except Exception as e:
            logger.error(f"Error creating OpenAI LLM: {e}")
            return None
    
    @staticmethod
    def get_default_llm() -> Optional[BaseLanguageModel]:
        """Get the default LLM based on configuration"""
        return LLMFactory.create_llm("auto")
    
    @staticmethod
    def get_available_providers() -> list:
        """Get list of available LLM providers"""
        providers = []
        
        if config.GEMINI_API_KEY:
            providers.append("gemini")
        
        if hasattr(config, 'OPENAI_API_KEY') and config.OPENAI_API_KEY:
            providers.append("openai")
        
        return providers 