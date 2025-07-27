import time
import json
import asyncio
from fastapi import Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from render_relay.utils.get_logger import get_logger
from app.factory.service_factory import service_factory
from app.factory.workflow_factory import workflow_factory
from typing import Optional

logger = get_logger("chat_api")

class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = None
    stream: Optional[bool] = False

async def POST(request: Request, chat_request: ChatRequest):
    """Chat with an agent - creates session if needed, sends message"""
    start_time = time.time()
    logger.info(f"🚀 Chat POST request started - session_id: {chat_request.session_id}, message_length: {len(chat_request.message)}, stream: {chat_request.stream}")
    
    # If streaming is requested, use the streaming endpoint
    if chat_request.stream:
        return await stream_chat(request, chat_request)
    
    try:
        # Get workflow service directly from workflow factory
        service_start = time.time()
        logger.debug("🔧 Getting workflow service...")
        workflow = workflow_factory.get_agent_workflow()
        service_time = time.time() - service_start
        init_time = service_start - start_time
        logger.debug(f"✅ Workflow service retrieved in {service_time:.3f}s")
        
        # If no session_id provided, create a new session
        if not chat_request.session_id:
            logger.info("🆕 Creating new session...")
            session_start = time.time()
            # Create session with the initial message
            session_result = await workflow.create_session(chat_request.message)
            session_time = time.time() - session_start
            logger.info(f"✅ Session created in {session_time:.3f}s")
            
            if session_result["status"] == "error":
                logger.error(f"❌ Session creation failed: {session_result}")
                return session_result
            
            total_time = time.time() - start_time
            logger.info(f"🎉 Chat POST completed successfully in {total_time:.3f}s (init: {init_time:.3f}s, service: {service_time:.3f}s, session: {session_time:.3f}s)")
            return {
                "status": "success",
                "session_id": session_result["session_id"],
                "response": session_result.get("agent_state", {}).get("messages", [])[-1].get("content", "") if session_result.get("agent_state", {}).get("messages") else "",
                "new_session": True,
                "agent_state": session_result["agent_state"]
            }
        else:
            logger.info(f"📝 Processing message in existing session {chat_request.session_id}...")
            process_start = time.time()
            # Use existing session
            result = await workflow.process_message(chat_request.session_id, chat_request.message)
            process_time = time.time() - process_start
            logger.info(f"✅ Message processed in {process_time:.3f}s")
            result["new_session"] = False
            
            total_time = time.time() - start_time
            logger.info(f"🎉 Chat POST completed successfully in {total_time:.3f}s (init: {init_time:.3f}s, service: {service_time:.3f}s, process: {process_time:.3f}s)")
            return result
            
    except Exception as e:
        total_time = time.time() - start_time
        logger.error(f"❌ Chat POST failed after {total_time:.3f}s: {str(e)}", exc_info=True)
        return {
            "status": "error",
            "message": f"Chat failed: {str(e)}"
        }

async def stream_chat(request: Request, chat_request: ChatRequest):
    """Stream chat with an agent - provides real-time updates"""
    async def generate_stream():
        start_time = time.time()
        logger.info(f"🚀 Streaming chat started - session_id: {chat_request.session_id}, message_length: {len(chat_request.message)}")
        
        try:
            # Get workflow service directly from workflow factory
            workflow = workflow_factory.get_agent_workflow()
            
            # Send initial status
            yield f"data: {json.dumps({'type': 'status', 'message': 'Initializing...', 'timestamp': time.time()})}\n\n"
            
            # If no session_id provided, create a new session
            if not chat_request.session_id:
                yield f"data: {json.dumps({'type': 'status', 'message': 'Creating new session...', 'timestamp': time.time()})}\n\n"
                
                # Create session with the initial message
                session_result = await workflow.create_session(chat_request.message)
                
                if session_result["status"] == "error":
                    yield f"data: {json.dumps({'type': 'error', 'message': session_result['message'], 'timestamp': time.time()})}\n\n"
                    return
                
                session_id = session_result["session_id"]
                yield f"data: {json.dumps({'type': 'session_created', 'session_id': session_id, 'timestamp': time.time()})}\n\n"
                
                # Get the response from the created session
                response = session_result.get("agent_state", {}).get("messages", [])[-1].get("content", "") if session_result.get("agent_state", {}).get("messages") else ""
                
                # Stream the response
                yield f"data: {json.dumps({'type': 'response_start', 'timestamp': time.time()})}\n\n"
                
                # Simulate streaming the response (since we already have it)
                words = response.split()
                for i, word in enumerate(words):
                    yield f"data: {json.dumps({'type': 'response_chunk', 'content': word + ' ', 'is_complete': i == len(words) - 1, 'timestamp': time.time()})}\n\n"
                    await asyncio.sleep(0.05)  # Small delay for streaming effect
                
                yield f"data: {json.dumps({'type': 'response_complete', 'full_response': response, 'timestamp': time.time()})}\n\n"
                
            else:
                yield f"data: {json.dumps({'type': 'status', 'message': 'Processing message...', 'timestamp': time.time()})}\n\n"
                
                # Use streaming workflow processing
                async for update in workflow.process_message_stream(chat_request.session_id, chat_request.message):
                    yield f"data: {json.dumps(update)}\n\n"
            
            total_time = time.time() - start_time
            logger.info(f"🎉 Streaming chat completed successfully in {total_time:.3f}s")
            
        except Exception as e:
            total_time = time.time() - start_time
            logger.error(f"❌ Streaming chat failed after {total_time:.3f}s: {str(e)}", exc_info=True)
            yield f"data: {json.dumps({'type': 'error', 'message': f'Chat failed: {str(e)}', 'timestamp': time.time()})}\n\n"
    
    return StreamingResponse(
        generate_stream(),
        media_type="text/plain",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Content-Type": "text/event-stream",
        }
    )

async def GET(request: Request, session_id: str):
    """Get chat messages for a session"""
    try:
        # Get unified session service directly from service factory
        session_service = service_factory.get_service('session')
        
        result = await session_service.get_session_messages(session_id)
        return result
        
    except Exception as e:
        return {
            "status": "error",
            "message": f"Failed to get chat messages: {str(e)}"
        }

