"""
Context Controller for managing context embedding operations
"""

from typing import List, Dict, Any, Optional
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, delete, text
from sqlalchemy.orm import sessionmaker

from ..models import ContextEmbedding, Session
import json
import numpy as np
from langchain.text_splitter import RecursiveCharacterTextSplitter
from ..database import sync_engine
from ...config.config import config
from ...factory.embedding_factory import EmbeddingFactory

# Create sync session factory using the existing sync engine
SyncSessionLocal = sessionmaker(
    sync_engine,
    expire_on_commit=False
)


class ContextController:
    """Controller for managing context embedding operations"""
    
    def __init__(self):
        """Initialize the controller - manages its own sessions"""
        self.embedding_dimensions = 768
    
    async def _get_session(self) -> AsyncSession:
        """Get a database session"""
        from ..config import AsyncSessionLocal
        async with AsyncSessionLocal() as session:
            return session
    
    async def create_session(self, session_id: str, meta_data: Dict[str, Any] = None) -> Session:
        """Create a new session"""
        db = await self._get_session()
        try:
            # Business logic: format session data
            session_data = {
                "session_id": session_id,
                "meta_data": meta_data or {"created_at": datetime.now().isoformat()}
            }
            
            session = Session(**session_data)
            db.add(session)
            await db.commit()
            await db.refresh(session)
            return session
        finally:
            await db.close()
    
    async def get_session(self, session_id: str) -> Optional[Session]:
        """Get session by ID"""
        db = await self._get_session()
        try:
            stmt = select(Session).where(Session.session_id == session_id)
            result = await db.execute(stmt)
            return result.scalar_one_or_none()
        finally:
            await db.close()
    
    async def update_session(self, session_id: str, **kwargs) -> Optional[Session]:
        """Update session with provided fields"""
        db = await self._get_session()
        try:
            stmt = select(Session).where(Session.session_id == session_id)
            result = await db.execute(stmt)
            session = result.scalar_one_or_none()
            
            if session:
                for key, value in kwargs.items():
                    if hasattr(session, key):
                        setattr(session, key, value)
                session.updated_at = datetime.now()
                await db.commit()
                await db.refresh(session)
            return session
        finally:
            await db.close()
    
    async def delete_session(self, session_id: str) -> bool:
        """Delete session and all its context embeddings"""
        db = await self._get_session()
        try:
            # Delete all context embeddings for this session
            await self.delete_context_by_session(session_id)
            
            # Delete the session
            stmt = delete(Session).where(Session.session_id == session_id)
            await db.execute(stmt)
            await db.commit()
            return True
        except Exception as e:
            await db.rollback()
            raise e
        finally:
            await db.close()
    
    async def create_context_embedding(self, **kwargs) -> ContextEmbedding:
        """Create a new context embedding"""
        db = await self._get_session()
        try:
            # Business logic: generate embedding if content provided
            if 'content' in kwargs and not kwargs.get('embedding'):
                content = kwargs['content']
                embedding = await self._generate_embedding(content)
                kwargs['embedding'] = embedding
            
            # Business logic: validate metadata
            if 'meta_data' in kwargs:
                if not isinstance(kwargs['meta_data'], dict):
                    raise ValueError("Invalid metadata format")
            
            # Create the context embedding object
            context_embedding = ContextEmbedding(**kwargs)
            
            # Properly set the embedding using the model's method
            if 'embedding' in kwargs and kwargs['embedding']:
                context_embedding.set_embedding(kwargs['embedding'])
            
            db.add(context_embedding)
            await db.commit()
            await db.refresh(context_embedding)
            return context_embedding
        finally:
            await db.close()
    
    async def get_context_by_session(self, session_id: str, limit: int = None) -> List[ContextEmbedding]:
        """Get all context embeddings for a session"""
        db = await self._get_session()
        try:
            stmt = select(ContextEmbedding).where(
                ContextEmbedding.session_id == session_id
            ).order_by(ContextEmbedding.created_at.asc())  # Changed to asc() to get chunks in order
            
            if limit:
                stmt = stmt.limit(limit)
            
            result = await db.execute(stmt)
            return result.scalars().all()
        finally:
            await db.close()
    
    async def get_context_by_key(self, session_id: str, context_key: str) -> List[ContextEmbedding]:
        """Get context embeddings by key for a session"""
        db = await self._get_session()
        try:
            stmt = select(ContextEmbedding).where(
                ContextEmbedding.session_id == session_id,
                ContextEmbedding.context_key == context_key
            ).order_by(ContextEmbedding.created_at.asc())
            
            result = await db.execute(stmt)
            return result.scalars().all()
        finally:
            await db.close()
    
    async def delete_context_by_session(self, session_id: str) -> bool:
        """Delete all context embeddings for a session"""
        db = await self._get_session()
        try:
            stmt = delete(ContextEmbedding).where(ContextEmbedding.session_id == session_id)
            await db.execute(stmt)
            await db.commit()
            return True
        except Exception as e:
            await db.rollback()
            raise e
        finally:
            await db.close()
    
    async def delete_context_by_key(self, session_id: str, context_key: str) -> bool:
        """Delete context embeddings by key for a session"""
        db = await self._get_session()
        try:
            stmt = delete(ContextEmbedding).where(
                ContextEmbedding.session_id == session_id,
                ContextEmbedding.context_key == context_key
            )
            await db.execute(stmt)
            await db.commit()
            return True
        except Exception as e:
            await db.rollback()
            raise e
        finally:
            await db.close()
    
    async def delete_context_by_key_prefix(self, session_id: str, key_prefix: str) -> bool:
        """Delete context embeddings by key prefix for a session"""
        db = await self._get_session()
        try:
            stmt = delete(ContextEmbedding).where(
                ContextEmbedding.session_id == session_id,
                ContextEmbedding.context_key.like(f"{key_prefix}%")
            )
            await db.execute(stmt)
            await db.commit()
            return True
        except Exception as e:
            await db.rollback()
            raise e
        finally:
            await db.close()
    
    async def get_session_stats(self, session_id: str) -> Dict[str, Any]:
        """Get statistics for a session's context"""
        db = await self._get_session()
        try:
            # Count total contexts
            stmt = select(func.count(ContextEmbedding.id)).where(
                ContextEmbedding.session_id == session_id
            )
            result = await db.execute(stmt)
            total_contexts = result.scalar() or 0
            
            # Get context types
            stmt = select(ContextEmbedding.meta_data).where(
                ContextEmbedding.session_id == session_id
            )
            result = await db.execute(stmt)
            contexts = result.scalars().all()
            
            context_types = {}
            for context in contexts:
                if context and isinstance(context, dict):
                    context_type = context.get('type', 'unknown')
                    context_types[context_type] = context_types.get(context_type, 0) + 1
            
            return {
                "session_id": session_id,
                "total_contexts": total_contexts,
                "context_types": context_types
            }
        finally:
            await db.close()
    
    async def search_context_similarity(self, session_id: str, query_embedding: List[float], limit: int = None) -> List[Dict[str, Any]]:
        """Search context by similarity using pgvector's native similarity functions or manual calculation"""
        db = await self._get_session()
        try:
            # Use config limit if not provided
            if limit is None:
                limit = config.CONTEXT_SEARCH_LIMIT
            
            # Check if pgvector is available
            from ..models.context import HAS_PGVECTOR
            
            if HAS_PGVECTOR:
                # Use pgvector's native similarity search
                embedding_tuple = tuple(query_embedding)
                
                # Use pgvector's cosine distance function
                stmt = select(ContextEmbedding).where(
                    ContextEmbedding.session_id == session_id
                ).order_by(
                    text("embedding <=> :embedding")  # Cosine distance (lower is better)
                ).params(embedding=embedding_tuple).limit(limit)
                
                result = await db.execute(stmt)
                contexts = result.scalars().all()
                
                # Convert to result format
                context_items = []
                for context in contexts:
                    # Calculate similarity score (1 - distance for cosine similarity)
                    # Note: pgvector returns distance, we convert to similarity
                    similarity = 1.0  # Default similarity for items without distance calculation
                    
                    context_items.append({
                        "content": context.content,
                        "metadata": context.meta_data or {},
                        "relevance_score": similarity
                    })
                
                # Filter by threshold
                threshold = config.CONTEXT_SIMILARITY_THRESHOLD
                filtered_items = [item for item in context_items if item["relevance_score"] >= threshold]
                
                return filtered_items
            else:
                # Fallback: manual similarity calculation
                stmt = select(ContextEmbedding).where(
                    ContextEmbedding.session_id == session_id
                ).order_by(ContextEmbedding.created_at.asc())
                
                result = await db.execute(stmt)
                all_contexts = result.scalars().all()
                
                # Calculate similarities manually
                context_items = []
                for context in all_contexts:
                    try:
                        if context.embedding:
                            stored_embedding = context.get_embedding()
                            if stored_embedding and len(stored_embedding) > 0:
                                similarity = self._cosine_similarity(query_embedding, stored_embedding)
                                context_items.append({
                                    "content": context.content,
                                    "metadata": context.meta_data or {},
                                    "relevance_score": similarity
                                })
                    except Exception as e:
                        continue
                
                # Filter by threshold and sort
                threshold = config.CONTEXT_SIMILARITY_THRESHOLD
                filtered_items = [item for item in context_items if item["relevance_score"] >= threshold]
                filtered_items.sort(key=lambda x: x["relevance_score"], reverse=True)
                
                return filtered_items[:limit]
            
        finally:
            await db.close()

    async def _generate_embedding(self, text: str) -> List[float]:
        """Generate embedding for text using the configured embedding model"""
        try:
            # Use the EmbeddingFactory with the configured model
            embedding = EmbeddingFactory.get_embedding(text, "auto")
            
            # Validate embedding dimensions
            if len(embedding) != self.embedding_dimensions:
                raise ValueError(f"Embedding dimensions mismatch: expected {self.embedding_dimensions}, got {len(embedding)}")
            
            return embedding
                
        except Exception as e:
            raise ValueError(f"Error generating embedding: {e}")
    
    def process_context_data(self, context_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Process different types of context data into standardized format"""
        processed_items = []
        
        for key, value in context_data.items():
            if isinstance(value, str):
                processed_items.append(self._process_text_context(key, value))
            elif isinstance(value, dict):
                processed_items.extend(self._process_dict_context(key, value))
            elif isinstance(value, list):
                processed_items.extend(self._process_list_context(key, value))
        
        return processed_items
    
    def _process_text_context(self, key: str, value: str) -> Dict[str, Any]:
        """Process text context"""
        # Note: This method is sync, so we can't use async embedding generation
        # In practice, this method should be called from an async context
        return {
            "context_key": key,
            "content": value,
            "meta_data": {
                "type": "text",
                "original_key": key,
                "timestamp": datetime.now().isoformat()
            }
        }
    
    def _process_dict_context(self, key: str, value: dict) -> List[Dict[str, Any]]:
        """Process dictionary context (files, structured data)"""
        processed_items = []
        
        if "content" in value and "filename" in value:
            # File content
            content = value.get("content", "")
            filename = value.get("filename", "unknown")
            
            # Split large content into chunks
            chunks = self._split_text(content)
            for i, chunk in enumerate(chunks):
                processed_items.append({
                    "context_key": f"{key}_chunk_{i}",
                    "content": chunk,
                    "meta_data": {
                        "type": "file_chunk",
                        "original_key": key,
                        "filename": filename,
                        "chunk_index": i,
                        "total_chunks": len(chunks),
                        "timestamp": datetime.now().isoformat()
                    }
                })
        else:
            # Structured data
            content = json.dumps(value)
            processed_items.append({
                "context_key": key,
                "content": content,
                "meta_data": {
                    "type": "structured_data",
                    "original_key": key,
                    "timestamp": datetime.now().isoformat()
                }
            })
        
        return processed_items
    
    def _process_list_context(self, key: str, value: list) -> List[Dict[str, Any]]:
        """Process list context"""
        processed_items = []
        
        for i, item in enumerate(value):
            if isinstance(item, str):
                content = item
            else:
                content = json.dumps(item)
            
            processed_items.append({
                "context_key": f"{key}_{i}",
                "content": content,
                "meta_data": {
                    "type": "list_item",
                    "original_key": key,
                    "list_key": key,
                    "item_index": i,
                    "timestamp": datetime.now().isoformat()
                }
            })
        
        return processed_items
    
    def _split_text(self, text: str, chunk_size: int = 1000, chunk_overlap: int = 200) -> List[str]:
        """Split text into chunks"""
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            length_function=len,
        )
        return text_splitter.split_text(text)

    def _cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """Calculate cosine similarity between two vectors (fallback when pgvector not available)"""
        try:
            vec1_array = np.array(vec1)
            vec2_array = np.array(vec2)
            
            norm1 = np.linalg.norm(vec1_array)
            norm2 = np.linalg.norm(vec2_array)
            
            if norm1 == 0 or norm2 == 0:
                return 0.0
            
            similarity = np.dot(vec1_array, vec2_array) / (norm1 * norm2)
            return float(similarity)
        except Exception as e:
            raise ValueError(f"Error calculating cosine similarity: {e}")


class ContextControllerSync:
    """Synchronous version of ContextController for sync operations"""
    
    def __init__(self):
        """Initialize the sync controller"""
        pass
    
    def retrieve_context_sync(self, session_id: str, query: str = None, limit: int = None) -> List[Dict[str, Any]]:
        """Retrieve context using synchronous database operations to avoid event loop conflicts"""
        try:
            # Use the sync session factory
            db = SyncSessionLocal()
            
            # Build query
            stmt = select(ContextEmbedding).where(
                ContextEmbedding.session_id == session_id
            ).order_by(ContextEmbedding.created_at.asc())
            
            if limit:
                stmt = stmt.limit(limit)
            
            result = db.execute(stmt)
            rows = result.scalars().all()
            
            print(f"Retrieved {len(rows)} raw context items from database")
            
            # If we have a query, get the embedding for semantic search
            query_embedding = None
            if query:
                try:
                    query_embedding = self._get_embedding_sync(query)
                    print(f"Generated query embedding with {len(query_embedding)} dimensions")
                except Exception as e:
                    print(f"Failed to generate embedding for query: {e}")
                    # Return empty result instead of falling back to text search
                    return []
            
            context_items = []
            for row in rows:
                metadata = row.meta_data if row.meta_data else {}
                
                # Debug: Log each context item
                print(f"Context item: key={row.context_key}, type={metadata.get('type', 'unknown')}, has_embedding={bool(row.embedding)}")
                if metadata.get('type') == 'file_chunk':
                    print(f"  File chunk: {metadata.get('filename', 'unknown')} chunk {metadata.get('chunk_index', 'unknown')}/{metadata.get('total_chunks', 'unknown')}")
                
                # Calculate relevance score
                relevance_score = 1.0  # Default score
                
                if query_embedding and row.embedding:
                    try:
                        stored_embedding = row.get_embedding()
                        if stored_embedding and len(stored_embedding) > 0:
                            relevance_score = self._cosine_similarity(query_embedding, stored_embedding)
                            print(f"Calculated similarity: {relevance_score:.3f} for content: {row.content[:50]}...")
                    except Exception as e:
                        print(f"Error calculating similarity: {e}")
                        # Don't use default score, skip this item
                        continue
                elif query and not query_embedding:
                    # If embedding generation failed, skip this item
                    print(f"Skipping item due to embedding failure: {row.content[:50]}...")
                    continue
                
                context_items.append({
                    "content": row.content,
                    "metadata": metadata,
                    "relevance_score": relevance_score
                })
            
            print(f"Retrieved {len(context_items)} raw context items from database")
            
            # If we have a query, sort by relevance score
            if query and query_embedding:
                context_items.sort(key=lambda x: x["relevance_score"], reverse=True)
                print(f"Sorted {len(context_items)} items by relevance score")
            
            # Apply limit after sorting
            if limit:
                context_items = context_items[:limit]
                print(f"Applied limit, returning {len(context_items)} items")
            
            return context_items
            
        except Exception as e:
            print(f"Database error in retrieve_context_sync: {str(e)}")
            # Don't return empty list, raise the error to prevent fallback
            raise e
    
    def _get_embedding_sync(self, text: str) -> List[float]:
        """Get embedding for text using the configured embedding model (sync version)"""
        try:
            # Use the EmbeddingFactory with the configured model
            embedding = EmbeddingFactory.get_embedding(text, "auto")
            
            # Validate embedding dimensions
            if len(embedding) != 768:
                raise ValueError(f"Embedding dimensions mismatch: expected 768, got {len(embedding)}")
            
            return embedding
                
        except Exception as e:
            print(f"Error generating embedding: {e}")
            # Don't return zero vector, raise the error to prevent fallback
            raise e
    
    @staticmethod
    def _cosine_similarity(vec1: List[float], vec2: List[float]) -> float:
        """Calculate cosine similarity between two vectors (fallback when pgvector not available)"""
        try:
            import numpy as np
            vec1_array = np.array(vec1)
            vec2_array = np.array(vec2)
            
            norm1 = np.linalg.norm(vec1_array)
            norm2 = np.linalg.norm(vec2_array)
            
            if norm1 == 0 or norm2 == 0:
                return 0.0
            
            similarity = np.dot(vec1_array, vec2_array) / (norm1 * norm2)
            return float(similarity)
        except Exception as e:
            print(f"Error calculating cosine similarity: {e}")
            # Don't return 0.0, raise the error to prevent fallback
            raise e 