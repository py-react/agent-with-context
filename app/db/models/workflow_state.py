from typing import List, Dict, Any, Optional, Literal
from pydantic import BaseModel, Field
from datetime import datetime
from .agent_state import MessageRole, Message

class WorkflowStep(BaseModel):
    """Represents a step in the workflow"""
    step_id: str = Field(description="Unique identifier for the step")
    step_type: str = Field(description="Type of step (intent_analysis, tool_selection, tool_execution, response_generation)")
    status: Literal["pending", "running", "completed", "failed"] = Field(default="pending")
    input_data: Dict[str, Any] = Field(default_factory=dict)
    output_data: Dict[str, Any] = Field(default_factory=dict)
    error: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

class WorkflowState(BaseModel):
    """State for LangGraph workflow"""
    session_id: str = Field(description="Session identifier")
    user_message: str = Field(description="Current user message")
    conversation_history: List[Message] = Field(default_factory=list, description="Previous conversation messages")
    
    # Metadata for storing tools and other data
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata (tools, etc.)")
    
    # Workflow tracking
    current_step: Optional[str] = Field(default=None, description="Current step being executed")
    workflow_steps: List[WorkflowStep] = Field(default_factory=list, description="All workflow steps")
    steps: List[WorkflowStep] = Field(default_factory=list, description="All workflow steps (alias for workflow_steps)")
    
    # Intent analysis
    intent: Optional[str] = Field(default=None, description="Primary detected user intent")
    detected_intent: Optional[str] = Field(default=None, description="Primary detected user intent")
    detected_intents: List[str] = Field(default_factory=list, description="All detected user intents")
    secondary_intents: List[str] = Field(default_factory=list, description="Secondary intents identified in the message")
    confidence: float = Field(default=0.0, description="Confidence in intent detection")
    requires_context: bool = Field(default=False, description="Whether context lookup is needed")
    tool_requirements: List[str] = Field(default_factory=list, description="Tool names that might be needed")
    reasoning: str = Field(default="", description="Reasoning for the intent analysis")
    
    # Tool selection
    selected_tools: List[str] = Field(default_factory=list, description="Tool names selected for this request")
    tool_results: List[Dict[str, Any]] = Field(default_factory=list, description="Results from tool executions")
    
    # Response generation
    response: Optional[str] = Field(default=None, description="Final response to user")
    final_response: Optional[str] = Field(default=None, description="Final response to user")
    response_metadata: Dict[str, Any] = Field(default_factory=dict, description="Metadata about the response")
    
    # Workflow status
    workflow_status: Literal["initialized", "intent_analysis", "tool_selection", "tool_execution", "reasoning", "response_generation", "completed", "error"] = Field(default="initialized")
    
    # Loop prevention and iteration tracking
    iteration_count: int = Field(default=0, description="Number of tool execution iterations")
    max_iterations: int = Field(default=3, description="Maximum number of tool execution iterations")
    previous_tool_selections: List[List[str]] = Field(default_factory=list, description="Previous tool selections to prevent loops")
    
    # Timestamps
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    
    def add_step(self, step: WorkflowStep) -> None:
        """Add a workflow step"""
        self.workflow_steps.append(step)
        self.steps = self.workflow_steps  # Keep steps in sync
        self.updated_at = datetime.now()
    
    def update_step(self, step_id: str, **kwargs) -> None:
        """Update a workflow step"""
        for step in self.workflow_steps:
            if step.step_id == step_id:
                for key, value in kwargs.items():
                    if hasattr(step, key):
                        setattr(step, key, value)
                break
        self.updated_at = datetime.now()
    
    def get_step(self, step_id: str) -> Optional[WorkflowStep]:
        """Get a workflow step by ID"""
        for step in self.workflow_steps:
            if step.step_id == step_id:
                return step
        return None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            "session_id": self.session_id,
            "user_message": self.user_message,
            "conversation_history": [msg.dict() for msg in self.conversation_history],
            "metadata": self.metadata,
            "current_step": self.current_step,
            "workflow_steps": [step.dict() for step in self.workflow_steps],
            "detected_intent": self.detected_intent,
            "detected_intents": self.detected_intents,
            "confidence": self.confidence,
            "selected_tools": self.selected_tools,
            "tool_results": self.tool_results,
            "final_response": self.final_response,
            "response_metadata": self.response_metadata,
            "workflow_status": self.workflow_status,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat()
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "WorkflowState":
        """Create from dictionary"""
        # Convert conversation history back to Message objects
        if "conversation_history" in data:
            messages = []
            for msg_data in data["conversation_history"]:
                messages.append(Message(**msg_data))
            data["conversation_history"] = messages
        
        # Convert workflow steps back to WorkflowStep objects
        if "workflow_steps" in data:
            steps = []
            for step_data in data["workflow_steps"]:
                steps.append(WorkflowStep(**step_data))
            data["workflow_steps"] = steps
        
        # Convert timestamps
        if "created_at" in data and isinstance(data["created_at"], str):
            data["created_at"] = datetime.fromisoformat(data["created_at"])
        if "updated_at" in data and isinstance(data["updated_at"], str):
            data["updated_at"] = datetime.fromisoformat(data["updated_at"])
        
        return cls(**data) 