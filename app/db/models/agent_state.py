from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from datetime import datetime
from enum import Enum

class MessageRole(str, Enum):
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"

class AgentStatus(str, Enum):
    IDLE = "idle"
    PROCESSING = "processing"
    COMPLETED = "completed"
    ERROR = "error"

class Message(BaseModel):
    role: MessageRole
    content: str
    timestamp: datetime = Field(default_factory=datetime.now)
    metadata: Optional[Dict[str, Any]] = None

class AgentState(BaseModel):
    session_id: str
    messages: List[Message] = Field(default_factory=list)
    context: Dict[str, Any] = Field(default_factory=dict)
    status: AgentStatus = AgentStatus.IDLE
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }
    
    def add_message(self, role: MessageRole, content: str, metadata: Optional[Dict[str, Any]] = None):
        """Add a new message to the conversation"""
        message = Message(role=role, content=content, metadata=metadata)
        self.messages.append(message)
        self.updated_at = datetime.now()
    
    def update_status(self, status: AgentStatus):
        """Update the agent status"""
        self.status = status
        self.updated_at = datetime.now()
    
    def add_context(self, key: str, value: Any):
        """Add or update context information"""
        self.context[key] = value
        self.updated_at = datetime.now()
    
    def remove_context(self, key: str):
        """Remove context information"""
        if key in self.context:
            del self.context[key]
            self.updated_at = datetime.now()
    
    def get_context(self, key: str, default: Any = None) -> Any:
        """Get context information"""
        return self.context.get(key, default)
    
    def set_context(self, context: Dict[str, Any]):
        """Set the entire context"""
        self.context = context
        self.updated_at = datetime.now()
    
    def get_context_summary(self) -> str:
        """Get a human-readable summary of the context"""
        if not self.context:
            return "No context available"
        
        summary_parts = []
        for key, value in self.context.items():
            if isinstance(value, str):
                summary_parts.append(f"{key}: {value}")
            elif isinstance(value, dict):
                # Special handling for file objects
                if key.startswith("file_") and "filename" in value and "content" in value:
                    filename = value.get("filename", "unknown")
                    content = value.get("content", "")
                    file_type = value.get("file_type", "unknown")
                    summary_parts.append(f"File '{filename}' ({file_type}):\n{content}")
                else:
                    # Include details for other dictionaries
                    dict_items = []
                    for k, v in value.items():
                        dict_items.append(f"{k}: {v}")
                    summary_parts.append(f"{key}: {', '.join(dict_items)}")
            elif isinstance(value, list):
                # Special handling for files list
                if key == "files":
                    file_descriptions = []
                    for file_info in value:
                        filename = file_info.get("filename", "unknown")
                        file_type = file_info.get("file_type", "unknown")
                        description = file_info.get("description", "")
                        content = file_info.get("content", "")
                        file_descriptions.append(f"'{filename}' ({file_type}):\n{content}")
                    summary_parts.append(f"Files:\n" + "\n".join(file_descriptions))
                else:
                    summary_parts.append(f"{key}: {len(value)} items")
            else:
                summary_parts.append(f"{key}: {str(value)}")
        
        return "; ".join(summary_parts)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for Redis storage"""
        return {
            "session_id": self.session_id,
            "messages": [{
                "role": msg.role.value,
                "content": msg.content,
                "timestamp": msg.timestamp.isoformat(),
                "metadata": msg.metadata
            } for msg in self.messages],
            "context": self.context,
            "status": self.status.value,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat()
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AgentState":
        """Create AgentState from dictionary"""
        # Convert string status back to enum with fallback
        if "status" in data:
            if isinstance(data["status"], str):
                try:
                    data["status"] = AgentStatus(data["status"])
                except ValueError:
                    # If the status is not a valid enum value, default to IDLE
                    data["status"] = AgentStatus.IDLE
            elif data["status"] is None:
                # If status is None, default to IDLE
                data["status"] = AgentStatus.IDLE
        else:
            # If no status provided, default to IDLE
            data["status"] = AgentStatus.IDLE
        
        # Convert message dictionaries back to Message objects
        if "messages" in data:
            data["messages"] = [Message(**msg) for msg in data["messages"]]
        
        # Convert datetime strings back to datetime objects
        if "created_at" in data and isinstance(data["created_at"], str):
            data["created_at"] = datetime.fromisoformat(data["created_at"])
        if "updated_at" in data and isinstance(data["updated_at"], str):
            data["updated_at"] = datetime.fromisoformat(data["updated_at"])
        
        return cls(**data) 