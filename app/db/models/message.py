from sqlalchemy import Column, Integer, String, Text, DateTime, JSON, Index, func
from .base import Base

class ConversationMessage(Base):
    """Model for storing conversation messages in PostgreSQL"""
    __tablename__ = "conversation_messages"
    
    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String(255), nullable=False, index=True)
    role = Column(String(50), nullable=False)  # user, assistant, system
    content = Column(Text, nullable=False)
    timestamp = Column(DateTime, default=func.now())
    message_metadata = Column(JSON, nullable=True)  # Renamed from metadata to avoid SQLAlchemy conflict
    message_order = Column(Integer, nullable=False)  # To maintain conversation order
    
    # Indexes for performance
    __table_args__ = (
        Index('idx_conversation_messages_session', 'session_id'),
        Index('idx_conversation_messages_order', 'session_id', 'message_order'),
    ) 