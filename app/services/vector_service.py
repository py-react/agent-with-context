"""
Vector Service for managing vector operations and embeddings
"""

import os
import asyncio
from typing import List, Dict, Any, Optional
from datetime import datetime
import uuid
import json
import numpy as np
from langchain.text_splitter import RecursiveCharacterTextSplitter
from ..config.config import config
from .db_service import DatabaseService
from render_relay.utils.get_logger import get_logger
from ..factory.embedding_factory import EmbeddingFactory

logger = get_logger("vector_service")

class VectorService:
    """Service for managing context in PostgreSQL with JSON embeddings"""
    
    def __init__(self, db_service: Optional[DatabaseService] = None):
        self.db_service = db_service
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200,
            length_function=len,
        )
    
    async def store_context(self, session_id: str, context_data: Dict[str, Any]) -> bool:
        """Store context data as embeddings in PostgreSQL using repository pattern"""
        try:
            # First, ensure session exists
            session_controller = await self.db_service.session_controller
            session = await session_controller.get_session(session_id)
            if not session:
                await session_controller.create_session(
                    session_id=session_id,
                    metadata={"last_context_update": datetime.now().isoformat()}
                )
            else:
                # Update session metadata
                await session_controller.update_session(
                    session_id=session_id,
                    meta_data={"last_context_update": datetime.now().isoformat()}
                )
            
            # Process different types of context data
            for key, value in context_data.items():
                if isinstance(value, str):
                    # Simple text context
                    embedding = await self._get_embedding(value)
                    context_controller = await self.db_service.context_controller
                    await context_controller.create_context_embedding(
                        session_id=session_id,
                        context_key=key,
                        content=value,
                        metadata={
                            "type": "text",
                            "timestamp": datetime.now().isoformat()
                        }
                    )
                
                elif isinstance(value, dict):
                    # File or structured data
                    if "content" in value and "filename" in value:
                        # File content
                        content = value.get("content", "")
                        filename = value.get("filename", "unknown")
                        
                        # Split large content into chunks
                        chunks = self.text_splitter.split_text(content)
                        context_controller = await self.db_service.context_controller
                        for i, chunk in enumerate(chunks):
                            embedding = await self._get_embedding(chunk)
                            await context_controller.create_context_embedding(
                                session_id=session_id,
                                context_key=f"{key}_{i}",
                                content=chunk,
                                metadata={
                                    "type": "file_chunk",
                                    "filename": filename,
                                    "file_type": value.get("file_type", "unknown"),
                                    "chunk_index": i,
                                    "total_chunks": len(chunks),
                                    "original_key": key,
                                    "timestamp": datetime.now().isoformat()
                                }
                            )
                    else:
                        # Other structured data
                        content = str(value)
                        embedding = await self._get_embedding(content)
                        context_controller = await self.db_service.context_controller
                        await context_controller.create_context_embedding(
                            session_id=session_id,
                            context_key=key,
                            content=content,
                            metadata={
                                "type": "structured_data",
                                "timestamp": datetime.now().isoformat()
                            }
                        )
                
                elif isinstance(value, list):
                    # List of items
                    context_controller = await self.db_service.context_controller
                    for i, item in enumerate(value):
                        if isinstance(item, str):
                            content = item
                        else:
                            content = str(item)
                        
                        embedding = await self._get_embedding(content)
                        await context_controller.create_context_embedding(
                            session_id=session_id,
                            context_key=f"{key}_{i}",
                            content=content,
                            metadata={
                                "type": "list_item",
                                "list_key": key,
                                "item_index": i,
                                "timestamp": datetime.now().isoformat()
                            }
                        )
            
            return True
            
        except Exception as e:
            print(f"Error storing context: {e}")
            return False
    
    async def retrieve_context(self, session_id: str, query: str = None) -> List[Dict[str, Any]]:
        """Retrieve context with optional semantic search"""
        try:
            context_controller = await self.db_service.context_controller
            if query:
                # Semantic search using pgvector's native similarity
                query_embedding = await self._get_embedding(query)
                return await context_controller.search_context_similarity(session_id, query_embedding, config.CONTEXT_SEARCH_LIMIT)
            else:
                # Get all context
                contexts = await context_controller.get_context_by_session(session_id, config.DEFAULT_CONTEXT_LIMIT)
                
                context_items = []
                for context in contexts:
                    context_items.append({
                        "content": context.content,
                        "metadata": context.meta_data if context.meta_data else {},
                        "relevance_score": 1.0
                    })
                
                return context_items
                
        except Exception as e:
            print(f"Error retrieving context: {e}")
            return []
    
    async def delete_session_context(self, session_id: str) -> bool:
        """Delete all context for a session"""
        try:
            context_controller = await self.db_service.context_controller
            return await context_controller.delete_context_by_session(session_id)
        except Exception as e:
            print(f"Error deleting session context: {e}")
            return False
    
    async def _get_embedding(self, text: str) -> List[float]:
        """Get embedding for text using embedding factory"""
        try:
            return EmbeddingFactory.get_embedding(text, "auto")
        except Exception as e:
            logger.error(f"Error getting embedding: {e}")
            # Return a default embedding (zeros)
            return [0.0] * 768
    
    async def get_session_stats(self, session_id: str) -> Dict[str, Any]:
        """Get statistics for a session's context"""
        try:
            context_controller = await self.db_service.context_controller
            contexts = await context_controller.get_context_by_session(session_id)
            return {
                "total_contexts": len(contexts),
                "session_id": session_id
            }
        except Exception as e:
            print(f"Error getting session stats: {e}")
            return {"total_contexts": 0, "session_id": session_id} 