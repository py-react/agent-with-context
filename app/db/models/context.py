from sqlalchemy import Column, Integer, String, Text, DateTime, JSON, Index, func
from .base import Base
import json

# Try to import pgvector VECTOR type, fallback to Text if not available
try:
    from sqlalchemy.dialects.postgresql import VECTOR
    HAS_PGVECTOR = True
except ImportError:
    # Fallback: use Text column for storing embeddings as JSON
    VECTOR = Text
    HAS_PGVECTOR = False

class ContextEmbedding(Base):
    """Model for storing context embeddings in PostgreSQL with pgvector"""
    __tablename__ = "context_embeddings"
    
    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String(255), nullable=False, index=True)
    context_key = Column(String(255), nullable=False)
    content = Column(Text, nullable=False)
    
    # Use VECTOR if pgvector is available, otherwise use Text
    if HAS_PGVECTOR:
        embedding = Column(VECTOR(768), nullable=True)  # Use pgvector native type
    else:
        embedding = Column(Text, nullable=True)  # Store as JSON string
    
    meta_data = Column(JSON, nullable=True)  # Renamed from metadata to avoid SQLAlchemy conflict
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    # Indexes for performance
    __table_args__ = (
        Index('idx_context_embeddings_session', 'session_id'),
    )
    
    def set_embedding(self, embedding_list):
        """Set embedding as pgvector type or JSON string"""
        if embedding_list:
            if HAS_PGVECTOR:
                # Convert list to tuple for pgvector
                self.embedding = tuple(embedding_list)
            else:
                # Store as JSON string
                self.embedding = json.dumps(embedding_list)
    
    def get_embedding(self):
        """Get embedding as list of floats"""
        if not self.embedding:
            return None
        
        if HAS_PGVECTOR:
            # Convert tuple back to list
            return list(self.embedding)
        else:
            # Parse JSON string
            try:
                return json.loads(self.embedding)
            except (json.JSONDecodeError, TypeError):
                return None 