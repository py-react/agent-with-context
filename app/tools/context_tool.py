import asyncio
import threading
from langchain_core.tools import tool
from render_relay.utils.get_logger import get_logger
from ..db import ContextControllerSync
from ..config.config import config

logger = get_logger("context_tool")

@tool
def retrieve_session_context(session_id: str, query: str = None) -> str:
    """Retrieve relevant context from the current session's stored information. Use this when you need to access previous files, preferences, or session-specific information that was uploaded or mentioned earlier. Provide a query to search for specific information, or leave empty to get recent context. This is especially useful when users ask about frameworks, programming topics, documentation, or any technical subjects that might be covered in uploaded files. Examples: 'What files did I upload?', 'Show me my documents', 'What did I share?', 'Find information about Python', 'Search my uploaded content', 'What context do you have?'."""
    
    try:
        logger.debug(f"ContextTool: session_id={session_id}, query={query}")
        
        # Use the synchronous controller directly with config limit
        controller = ContextControllerSync()
        context_items = controller.retrieve_context_sync(session_id, query, config.DEFAULT_CONTEXT_LIMIT)
        
        logger.debug(f"ContextTool: retrieved {len(context_items) if context_items else 0} context items")
        
        if not context_items:
            return "No relevant context found for this session. The user may not have uploaded any files or context yet."
        
        # Debug: Show what we're returning
        logger.debug(f"Returning {len(context_items)} context items to LLM:")
        for i, item in enumerate(context_items[:5]):  # Show first 5 items
            metadata = item["metadata"]
            if metadata.get("type") == "file_chunk":
                logger.debug(f"  {i+1}. File: {metadata.get('filename', 'unknown')} chunk {metadata.get('chunk_index', 'unknown')}/{metadata.get('total_chunks', 'unknown')} (score: {item['relevance_score']:.3f})")
            else:
                logger.debug(f"  {i+1}. Context: {metadata.get('context_key', 'unknown')} (score: {item['relevance_score']:.3f})")
        
        # Format the results for better readability
        result_parts = []
        result_parts.append(f"Found {len(context_items)} relevant context items:")
        result_parts.append("=" * 50)
        
        for i, item in enumerate(context_items, 1):
            metadata = item["metadata"]
            content = item["content"]
            score = item["relevance_score"]
            
            # Format based on content type
            if metadata.get("type") == "file_chunk":
                filename = metadata.get("filename", "unknown")
                chunk_info = f" (chunk {metadata.get('chunk_index', 0) + 1}/{metadata.get('total_chunks', 1)})"
                result_parts.append(f"\n{i}. 📄 File: {filename}{chunk_info}")
                result_parts.append(f"   Relevance: {score:.3f}")
                result_parts.append(f"   Content: {content}")
            elif metadata.get("type") == "text":
                context_key = metadata.get("context_key", "unknown")
                original_key = metadata.get("original_key", context_key)
                result_parts.append(f"\n{i}. 📝 Context Key: {context_key}")
                if original_key != context_key:
                    result_parts.append(f"   Original Key: {original_key}")
                result_parts.append(f"   Relevance: {score:.3f}")
                result_parts.append(f"   Content: {content}")
            else:
                context_key = metadata.get("context_key", "unknown")
                original_key = metadata.get("original_key", context_key)
                result_parts.append(f"\n{i}. 📋 Context: {context_key}")
                if original_key != context_key:
                    result_parts.append(f"   Original Key: {original_key}")
                result_parts.append(f"   Relevance: {score:.3f}")
                result_parts.append(f"   Content: {content}")
            
            result_parts.append("-" * 30)
        
        return "\n".join(result_parts)
        
    except Exception as e:
        logger.error(f"Error retrieving context: {str(e)}")
        return f"Error retrieving context: {str(e)}" 