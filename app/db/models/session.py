from sqlalchemy import Column, Integer, String, DateTime, JSON, func
from .base import Base

class Session(Base):
    """Model for storing session metadata"""
    __tablename__ = "sessions"
    
    session_id = Column(String(255), primary_key=True, index=True)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    status = Column(String(50), default='active')
    meta_data = Column(JSON, nullable=True)  # Renamed from metadata to avoid SQLAlchemy conflict
    
    # Add conversation state fields
    conversation_status = Column(String(50), default='idle')  # idle, processing, completed, error
    message_count = Column(Integer, default=0)
    last_message_at = Column(DateTime, nullable=True) 