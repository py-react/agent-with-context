import time
import asyncio
from typing import Dict, Any, Optional, AsyncGenerator
from render_relay.utils.get_logger import get_logger
from ..db import AgentState, MessageRole, AgentStatus
# Service factory import removed to avoid circular imports

logger = get_logger("agent_workflow")

class AgentWorkflow:
    """Handles agent conversation workflows and state management"""
    
    def __init__(self, session_service=None, langgraph_workflow_service=None):
        from ..config.config import config
        self.max_context_length = config.MAX_CONTEXT_LENGTH
        self.session_service = session_service
        self.langgraph_workflow_service = langgraph_workflow_service
    
    def set_services(self, session_service, langgraph_workflow_service):
        """Set services via dependency injection"""
        self.session_service = session_service
        self.langgraph_workflow_service = langgraph_workflow_service
    
    def _get_services(self):
        """Get services from service factory if not directly injected"""
        # Services should be injected via dependency injection
        # This method is kept for compatibility but services must be set externally
        pass
    
    async def process_message_stream(self, session_id: str, user_message: str) -> AsyncGenerator[Dict[str, Any], None]:
        """Process a user message through the agent workflow with streaming updates"""
        start_time = time.time()
        logger.info(f"🔄 AgentWorkflow.process_message_stream started - session_id: {session_id}, message_length: {len(user_message)}")
        
        # Services should be injected via dependency injection
        
        if not all([self.session_service, self.langgraph_workflow_service]):
            logger.error("❌ Required services not configured")
            yield {
                "type": "error",
                "message": "Required services not configured",
                "timestamp": time.time()
            }
            return
        
        try:
            # Send initial status
            yield {
                "type": "status",
                "message": "Getting agent state...",
                "timestamp": time.time()
            }
            
            # Get current agent state using session service
            redis_start = time.time()
            logger.debug("📥 Getting agent state from session service...")
            agent_state = await self.session_service.get_agent_state(session_id)
            redis_time = time.time() - redis_start
            logger.debug(f"✅ Agent state retrieved in {redis_time:.3f}s")
            
            if not agent_state:
                logger.error(f"❌ Session {session_id} not found")
                yield {
                    "type": "error",
                    "message": "Session not found",
                    "timestamp": time.time()
                }
                return
            
            # Update status to processing
            yield {
                "type": "status",
                "message": "Updating agent status...",
                "timestamp": time.time()
            }
            
            logger.debug("🔄 Updating agent status to processing...")
            agent_state.update_status(AgentStatus.PROCESSING)
            await self.session_service.save_agent_state(session_id, agent_state)
            
            # Add user message
            yield {
                "type": "status",
                "message": "Adding user message...",
                "timestamp": time.time()
            }
            
            logger.debug("💬 Adding user message to agent state...")
            agent_state.add_message(MessageRole.USER, user_message)
            
            # Save user message immediately to ensure persistence
            logger.debug("💾 Saving user message to database...")
            await self.session_service.save_agent_state(session_id, agent_state)
            
            # Zero in-memory approach: don't load conversation history
            # Tools will fetch from database as needed
            conversation_history = []
            
            logger.debug("📚 Using zero in-memory approach - tools will fetch conversation history as needed")
            
            # Process message using LangGraph workflow with streaming
            yield {
                "type": "status",
                "message": "Starting workflow processing...",
                "timestamp": time.time()
            }
            
            workflow_start = time.time()
            logger.info("🚀 Starting LangGraph workflow processing with streaming...")
            
            # Variables to collect response and metadata from streaming
            final_response = ""
            workflow_metadata = {}
            workflow_state_data = {}
            tool_results = []
            
            # Use streaming workflow processing
            async for update in self.langgraph_workflow_service.process_message_stream(
                session_id, 
                user_message, 
                conversation_history
            ):
                # Pass through all updates from the workflow
                yield update
                
                # Collect response and metadata from streaming updates
                if update.get("type") == "response_complete":
                    final_response = update.get("full_response", "")
                elif update.get("type") == "step_complete":
                    step = update.get("step", "")
                    if step == "intent_analysis":
                        workflow_metadata.update(update.get("result", {}))
                    elif step == "tool_selection":
                        workflow_metadata["selected_tools"] = update.get("result", {}).get("selected_tools", [])
                    elif step == "response_generation":
                        workflow_metadata["response_length"] = update.get("result", {}).get("response_length", 0)
                elif update.get("type") == "tool_call_complete":
                    tool_results.append({
                        "tool": update.get("tool"),
                        "result": update.get("output"),
                        "status": "success"
                    })
                elif update.get("type") == "tool_call_error":
                    tool_results.append({
                        "tool": update.get("tool"),
                        "result": None,
                        "status": "error",
                        "error": update.get("error")
                    })
            
            workflow_time = time.time() - workflow_start
            logger.info(f"✅ LangGraph workflow streaming completed in {workflow_time:.3f}s")
            
            # Create workflow result from collected data
            workflow_metadata["tool_calls"] = tool_results
            workflow_metadata["requires_tools"] = len(tool_results) > 0
            
            workflow_result = {
                "status": "success",
                "response": final_response,
                "metadata": workflow_metadata,
                "workflow_state": workflow_state_data
            }
            
            # Add assistant response with metadata
            yield {
                "type": "status",
                "message": "Saving response...",
                "timestamp": time.time()
            }
            
            logger.debug("💬 Adding assistant response to agent state...")
            agent_state.add_message(
                MessageRole.ASSISTANT,
                workflow_result["response"],
                metadata={
                    "requires_tools": workflow_result.get("metadata", {}).get("requires_tools", False),
                    "tool_calls": workflow_result.get("metadata", {}).get("tool_calls", []),
                    "intent": workflow_result.get("metadata", {}).get("intent"),
                    "confidence": workflow_result.get("metadata", {}).get("confidence"),
                    "workflow_status": workflow_result.get("workflow_state", {}).get("workflow_status"),
                    "session_context_used": workflow_result.get("metadata", {}).get("session_context_used", False),
                    "status": workflow_result.get("status", "success")
                }
            )
            
            # Update status to completed
            logger.debug("✅ Updating agent status to completed...")
            agent_state.update_status(AgentStatus.COMPLETED)
            
            # Save updated state using session service
            save_start = time.time()
            logger.debug("💾 Saving updated agent state via session service...")
            await self.session_service.save_agent_state(session_id, agent_state)
            save_time = time.time() - save_start
            logger.debug(f"✅ Agent state saved in {save_time:.3f}s")
            
            total_time = time.time() - start_time
            logger.info(f"🎉 AgentWorkflow.process_message_stream completed successfully in {total_time:.3f}s")
            
            # Send final completion message
            yield {
                "type": "complete",
                "session_id": session_id,
                "response": workflow_result["response"],
                "metadata": {
                    "requires_tools": workflow_result.get("metadata", {}).get("requires_tools", False),
                    "tool_calls": workflow_result.get("metadata", {}).get("tool_calls", []),
                    "intent": workflow_result.get("metadata", {}).get("intent"),
                    "confidence": workflow_result.get("metadata", {}).get("confidence"),
                    "workflow_status": workflow_result.get("workflow_state", {}).get("workflow_status"),
                    "session_context_used": workflow_result.get("metadata", {}).get("session_context_used", False),
                    "status": workflow_result.get("status", "success")
                },
                "timestamp": time.time()
            }
            
        except Exception as e:
            total_time = time.time() - start_time
            logger.error(f"❌ AgentWorkflow.process_message_stream failed after {total_time:.3f}s: {str(e)}", exc_info=True)
            
            # Update status to error
            if agent_state:
                agent_state.update_status(AgentStatus.ERROR)
                await self.session_service.save_agent_state(session_id, agent_state)
            
            yield {
                "type": "error",
                "message": f"Workflow processing failed: {str(e)}",
                "timestamp": time.time()
            }

    async def process_message(self, session_id: str, user_message: str) -> Dict[str, Any]:
        """Process a user message through the agent workflow"""
        start_time = time.time()
        logger.info(f"🔄 AgentWorkflow.process_message started - session_id: {session_id}, message_length: {len(user_message)}")
        
        # Services should be injected via dependency injection
        
        if not all([self.session_service, self.langgraph_workflow_service]):
            logger.error("❌ Required services not configured")
            return {
                "status": "error",
                "message": "Required services not configured"
            }
        
        try:
            # Get current agent state using session service
            redis_start = time.time()
            logger.debug("📥 Getting agent state from session service...")
            agent_state = await self.session_service.get_agent_state(session_id)
            redis_time = time.time() - redis_start
            logger.debug(f"✅ Agent state retrieved in {redis_time:.3f}s")
            
            if not agent_state:
                logger.error(f"❌ Session {session_id} not found")
                return {
                    "status": "error",
                    "message": "Session not found"
                }
            
            # Update status to processing
            logger.debug("🔄 Updating agent status to processing...")
            agent_state.update_status(AgentStatus.PROCESSING)
            await self.session_service.save_agent_state(session_id, agent_state)
            
            # Add user message
            logger.debug("💬 Adding user message to agent state...")
            agent_state.add_message(MessageRole.USER, user_message)
            
            # Save user message immediately to ensure persistence
            logger.debug("💾 Saving user message to database...")
            await self.session_service.save_agent_state(session_id, agent_state)
            
            # Zero in-memory approach: don't load conversation history
            # Tools will fetch from database as needed
            conversation_history = []
            
            logger.debug("📚 Using zero in-memory approach - tools will fetch conversation history as needed")
            
            # Process message using LangGraph workflow
            workflow_start = time.time()
            logger.info("🚀 Starting LangGraph workflow processing...")
            workflow_result = await self.langgraph_workflow_service.process_message(
                session_id, 
                user_message, 
                conversation_history
            )
            workflow_time = time.time() - workflow_start
            logger.info(f"✅ LangGraph workflow completed in {workflow_time:.3f}s")
            
            # Add assistant response with metadata
            logger.debug("💬 Adding assistant response to agent state...")
            agent_state.add_message(
                MessageRole.ASSISTANT,
                workflow_result["response"],
                metadata={
                    "requires_tools": workflow_result.get("metadata", {}).get("requires_tools", False),
                    "tool_calls": workflow_result.get("metadata", {}).get("tool_calls", []),
                    "intent": workflow_result.get("metadata", {}).get("intent"),
                    "confidence": workflow_result.get("metadata", {}).get("confidence"),
                    "workflow_status": workflow_result.get("workflow_state", {}).get("workflow_status"),
                    "session_context_used": workflow_result.get("metadata", {}).get("session_context_used", False),
                    "status": workflow_result.get("status", "success")
                }
            )
            
            # Update status to completed
            logger.debug("✅ Updating agent status to completed...")
            agent_state.update_status(AgentStatus.COMPLETED)
            
            # Save updated state using session service
            save_start = time.time()
            logger.debug("💾 Saving updated agent state via session service...")
            await self.session_service.save_agent_state(session_id, agent_state)
            save_time = time.time() - save_start
            logger.debug(f"✅ Agent state saved in {save_time:.3f}s")
            
            total_time = time.time() - start_time
            logger.info(f"🎉 AgentWorkflow.process_message completed successfully in {total_time:.3f}s (redis: {redis_time:.3f}s, workflow: {workflow_time:.3f}s, save: {save_time:.3f}s)")
            
            return {
                "status": "success",
                "session_id": session_id,
                "response": workflow_result["response"],
                "metadata": {
                    "requires_tools": workflow_result.get("metadata", {}).get("requires_tools", False),
                    "tool_calls": workflow_result.get("metadata", {}).get("tool_calls", []),
                    "intent": workflow_result.get("metadata", {}).get("intent"),
                    "confidence": workflow_result.get("metadata", {}).get("confidence"),
                    "workflow_status": workflow_result.get("workflow_state", {}).get("workflow_status"),
                    "session_context_used": workflow_result.get("metadata", {}).get("session_context_used", False),
                    "status": workflow_result.get("status", "success")
                },
                "agent_state": agent_state.to_dict()
            }
            
        except Exception as e:
            total_time = time.time() - start_time
            logger.error(f"❌ AgentWorkflow.process_message failed after {total_time:.3f}s: {str(e)}", exc_info=True)
            
            # Update status to error
            if agent_state:
                agent_state.update_status(AgentStatus.ERROR)
                await self.session_service.save_agent_state(session_id, agent_state)
            
            return {
                "status": "error",
                "message": f"Workflow processing failed: {str(e)}"
            }
    
    async def create_session(self, initial_message: Optional[str] = None, initial_context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Create a new agent session with optional initial context"""
        # Services should be injected via dependency injection
        
        if not all([self.session_service, self.langgraph_workflow_service]):
            return {
                "status": "error",
                "message": "Required services not configured"
            }
        
        try:
            import uuid
            session_id = str(uuid.uuid4())
            
            # Create new agent state
            agent_state = AgentState(session_id=session_id)
            
            # Store initial context using session service if provided
            if initial_context:
                await self.session_service.store_context(session_id, initial_context)
            
            # Add initial message if provided
            if initial_message:
                agent_state.add_message(MessageRole.USER, initial_message)
                
                # Save user message immediately to ensure persistence
                logger.debug("💾 Saving initial user message to database...")
                await self.session_service.save_agent_state(session_id, agent_state)
                
                # Process initial message using LangGraph workflow
                workflow_result = await self.langgraph_workflow_service.process_message(
                    session_id, 
                    initial_message, 
                    [msg.dict() for msg in agent_state.messages]
                )
                
                agent_state.add_message(
                    MessageRole.ASSISTANT,
                    workflow_result["response"],
                    metadata={
                        "requires_tools": workflow_result.get("metadata", {}).get("requires_tools", False),
                        "tool_calls": workflow_result.get("metadata", {}).get("tool_calls", []),
                        "intent": workflow_result.get("metadata", {}).get("intent"),
                        "confidence": workflow_result.get("metadata", {}).get("confidence"),
                        "workflow_status": workflow_result.get("workflow_state", {}).get("workflow_status"),
                        "session_context_used": workflow_result.get("metadata", {}).get("session_context_used", False),
                        "status": workflow_result.get("status", "success")
                    }
                )
            
            # Save to session service (which handles both Redis and database)
            success = await self.session_service.save_agent_state(session_id, agent_state)
            
            if not success:
                return {
                    "status": "error",
                    "message": "Failed to create session"
                }
            
            return {
                "status": "success",
                "session_id": session_id,
                "message": "Session created successfully",
                "context": initial_context if initial_context else {},
                "agent_state": agent_state.to_dict()
            }
            
        except Exception as e:
            return {
                "status": "error",
                "message": f"Failed to create session: {str(e)}"
            }
    
    def _truncate_context(self, agent_state: AgentState) -> AgentState:
        """Truncate context to keep only recent messages"""
        if len(agent_state.messages) > self.max_context_length:
            # Keep system messages and recent messages
            system_messages = [msg for msg in agent_state.messages if msg.role == MessageRole.SYSTEM]
            recent_messages = agent_state.messages[-self.max_context_length:]
            
            # Combine system messages with recent messages
            agent_state.messages = system_messages + recent_messages[-self.max_context_length:]
        
        return agent_state

# Global workflow instance (without services - will be injected)
agent_workflow = AgentWorkflow() 