from fastapi import Request, UploadFile, File, Form
from pydantic import BaseModel
from app.factory.service_factory import service_factory
from typing import Dict, Any, Optional, List
import os
import uuid
from datetime import datetime
import mimetypes
import io
import hashlib
import docx
from docx import Document
import PyPDF2

class ContextRequest(BaseModel):
    context: Optional[Dict[str, Any]] = None

class ContextUpdateRequest(BaseModel):
    key: Optional[str] = None
    value: Optional[Any] = None


class ContextRemoveRequest(BaseModel):
    key: str


class FileUploadRequest(BaseModel):
    description: Optional[str] = None
    tags: Optional[List[str]] = None


class FileContext(BaseModel):
    file_id: str
    filename: str
    content: str
    file_type: str
    file_size: int
    description: Optional[str] = None
    tags: Optional[List[str]] = None
    uploaded_at: datetime
    content_summary: Optional[str] = None

# File processing utilities - consolidated into process_file function


async def process_file(file: UploadFile) -> FileContext:
    """Process uploaded file and return FileContext"""
    # Get file info
    filename = file.filename
    file_type = "unknown"

    # Determine file type
    if filename:
        mime_type, _ = mimetypes.guess_type(filename)
        if mime_type:
            file_type = mime_type.split('/')[-1]

    # Read file content first
    content_bytes = await file.read()
    content = ""

    # Process based on file extension
    if filename:
        ext = filename.lower().split('.')[-1]

        if ext in ['txt', 'md', 'json', 'csv', 'log']:
            # Text files
            try:
                content = content_bytes.decode('utf-8')
            except UnicodeDecodeError:
                # Try with different encodings
                for encoding in ['latin-1', 'cp1252', 'iso-8859-1']:
                    try:
                        content = content_bytes.decode(encoding)
                        break
                    except UnicodeDecodeError:
                        continue
                if not content:
                    raise ValueError("Unable to decode file content")
            file_type = "text"
        elif ext in ['docx']:
            try:
                doc = Document(io.BytesIO(content_bytes))
                text_content = []
                for paragraph in doc.paragraphs:
                    if paragraph.text.strip():
                        text_content.append(paragraph.text)
                content = '\n'.join(text_content)
            except Exception as e:
                raise ValueError(f"Error processing DOCX file: {str(e)}")
            file_type = "docx"
        elif ext in ['pdf']:

            try:
                pdf_reader = PyPDF2.PdfReader(io.BytesIO(content_bytes))
                text_content = []
                for page in pdf_reader.pages:
                    text_content.append(page.extract_text())
                content = '\n'.join(text_content)
            except Exception as e:
                raise ValueError(f"Error processing PDF file: {str(e)}")
            file_type = "pdf"
        else:
            # Try as text file
            try:
                content = content_bytes.decode('utf-8')
                file_type = "text"
            except UnicodeDecodeError:
                raise ValueError(f"Unsupported file type: {ext}")

    # Get file size
    file_size = len(content_bytes)

    # Generate file ID
    file_id = str(uuid.uuid4())

    # Create content summary (include full content for better LLM access)
    content_summary = content

    return FileContext(
        file_id=file_id,
        filename=filename or "unknown",
        content=content,
        file_type=file_type,
        file_size=file_size,
        uploaded_at=datetime.now(),
        content_summary=content_summary
    )


async def GET(request: Request, session_id: str, file_id: str = None):
    """Get context for a session or a specific file if file_id is provided"""
    try:
        session_service = service_factory.get_service('session')
        # Retrieve context from vector database using new service (get all items)
        context_data = await session_service.retrieve_context(session_id)
        
        if not context_data:
            return {
                "status": "success",
                "session_id": session_id,
                "context": {},
                "message": "No context found in vector database"
            }

        # If file_id is provided, return specific file
        if file_id:
            file_key = f"file_{file_id}"
            file_data = None
            
            for item in context_data:
                if item.get("metadata", {}).get("original_key") == file_key:
                    file_data = item.get("content")
                    break

            if not file_data:
                return {
                    "status": "error",
                    "message": "File not found in context"
                }

            return {
                "status": "success",
                "session_id": session_id,
                "file_id": file_id,
                "file_data": file_data
            }

        # Otherwise return full context
        return {
            "status": "success",
            "session_id": session_id,
            "context": context_data,
            "message": "Context retrieved from vector database"
        }

    except Exception as e:
        return {
            "status": "error",
            "message": f"Failed to get context: {str(e)}"
        }


async def POST(request: Request, session_id: str, file: Optional[UploadFile] = File(None), description: Optional[str] = Form(None), tags: Optional[str] = Form(None)):
    """Append context to a session (adds new context without replacing existing) or upload a new file if file is provided"""
    try:
        # Get services
        session_service = service_factory.get_service('session')
        
        # If file is provided, treat as file upload
        if file is not None:
            file_context = await process_file(file)
            if description:
                file_context.description = description
            if tags:
                file_context.tags = [tag.strip()
                                     for tag in tags.split(',') if tag.strip()]
            
            # Store file context in vector database only (no Redis)
            file_context_data = {
                f"file_{file_context.file_id}": {
                    "filename": file_context.filename,
                    "content": file_context.content,
                    "file_type": file_context.file_type,
                    "description": file_context.description,
                    "tags": file_context.tags,
                    "file_size": file_context.file_size,
                    "uploaded_at": file_context.uploaded_at.isoformat(),
                    "content_summary": file_context.content_summary
                }
            }
            vector_success = await session_service.store_context(session_id, file_context_data)
            
            if not vector_success:
                return {
                    "status": "error",
                    "message": "Failed to store file in vector database"
                }
            
            return {
                "status": "success",
                "session_id": session_id,
                "file_id": file_context.file_id,
                "filename": file_context.filename,
                "file_type": file_context.file_type,
                "file_size": file_context.file_size,
                "description": file_context.description,
                "tags": file_context.tags,
                "content_summary": file_context.content_summary,
                "vector_stored": vector_success,
                "message": f"File '{file_context.filename}' uploaded successfully to context"
            }
        else:
            # Read context from request body
            try:
                body = await request.json()
                context_data = body.get("context")
                
                if context_data is not None:
                    # For POST, we append context (don't replace existing)
                    # Check if any keys already exist and warn user
                    existing_context = await session_service.retrieve_context(session_id)
                    existing_keys = set()
                    for item in existing_context:
                        if item.get("metadata", {}).get("original_key"):
                            existing_keys.add(item["metadata"]["original_key"])
                    
                    # Filter out keys that already exist to prevent duplicates
                    new_context_data = {}
                    duplicate_keys = []
                    for key, value in context_data.items():
                        if key in existing_keys:
                            duplicate_keys.append(key)
                        else:
                            new_context_data[key] = value
                    
                    if not new_context_data:
                        return {
                            "status": "error",
                            "message": f"All provided keys already exist in context: {list(context_data.keys())}. Use PUT to update existing keys."
                        }
                    
                    # Store new context in vector database
                    vector_success = await session_service.store_context(session_id, new_context_data)
                    
                    if not vector_success:
                        return {
                            "status": "error",
                            "message": "Failed to store context in vector database"
                        }
                    
                    response_message = f"Context appended successfully to vector database"
                    if duplicate_keys:
                        response_message += f". Skipped duplicate keys: {duplicate_keys}"
                    
                    return {
                        "status": "success",
                        "session_id": session_id,
                        "context": new_context_data,
                        "duplicate_keys": duplicate_keys,
                        "vector_stored": vector_success,
                        "message": response_message
                    }
                else:
                    return {
                        "status": "error",
                        "message": "No context data provided in request body"
                    }
            except Exception as e:
                return {
                    "status": "error",
                    "message": f"Error processing context data: {str(e)}"
                }
    except Exception as e:
        return {
            "status": "error",
            "message": f"Error setting context: {str(e)}"
        }


async def PUT(request: Request, session_id: str, file: Optional[UploadFile] = File(None), description: Optional[str] = Form(None), tags: Optional[str] = Form(None), file_id: Optional[str] = Form(None)):
    """Update a specific context key for a session or update/replace a file if file is provided"""
    try:
        # Get services
        session_service = service_factory.get_service('session')

        # If file is provided, treat as file update (requires file_id)
        if file is not None:
            if not file_id:
                return {
                    "status": "error",
                    "message": "file_id is required when updating a file"
                }
            
            file_context = await process_file(file)
            if description:
                file_context.description = description
            if tags:
                file_context.tags = [tag.strip()
                                     for tag in tags.split(',') if tag.strip()]
            
            # First, delete the existing file from vector database
            delete_success = await session_service.delete_context(session_id, f"file_{file_id}")
            
            # Store updated file context in vector database
            file_context_data = {
                f"file_{file_id}": {
                    "filename": file_context.filename,
                    "content": file_context.content,
                    "file_type": file_context.file_type,
                    "description": file_context.description,
                    "tags": file_context.tags,
                    "file_size": file_context.file_size,
                    "uploaded_at": file_context.uploaded_at.isoformat(),
                    "content_summary": file_context.content_summary
                }
            }
            vector_success = await session_service.store_context(session_id, file_context_data)
            
            if not vector_success:
                return {
                    "status": "error",
                    "message": "Failed to update file in vector database"
                }
            
            return {
                "status": "success",
                "session_id": session_id,
                "file_id": file_id,
                "filename": file_context.filename,
                "file_type": file_context.file_type,
                "file_size": file_context.file_size,
                "description": file_context.description,
                "tags": file_context.tags,
                "content_summary": file_context.content_summary,
                "vector_stored": vector_success,
                "message": f"File '{file_context.filename}' updated successfully in vector database"
            }
        else:
            # Read context update from request body (only if no file is provided)
            try:
                body = await request.json()
                key = body.get("key")
                value = body.get("value")
                
                if key is not None and value is not None:
                    # First, delete existing context with this key from vector database
                    delete_success = await session_service.delete_context(session_id, key)
                    
                    # Store updated context in vector database using context service
                    context_data = {key: value}
                    vector_success = await session_service.store_context(session_id, context_data)
                    
                    if not vector_success:
                        return {
                            "status": "error",
                            "message": "Failed to store context in vector database"
                        }
                    
                    return {
                        "status": "success",
                        "session_id": session_id,
                        "context": context_data,
                        "message": f"Context key '{key}' updated successfully in vector database"
                    }
                else:
                    return {
                        "status": "error",
                        "message": "Both key and value are required in request body"
                    }
            except Exception as e:
                return {
                    "status": "error",
                    "message": f"Error processing context update: {str(e)}"
                }
    except Exception as e:
        return {
            "status": "error",
            "message": f"Failed to update context or file: {str(e)}"
        }


async def DELETE(request: Request, session_id: str, file_id: str = None):
    """Remove a specific context key or file from a session"""
    try:
        # Get services
        session_service = service_factory.get_service('session')
        
        # If file_id is provided, remove specific file
        if file_id:
            file_key = f"file_{file_id}"
            
            # Remove file from vector database
            vector_success = await session_service.delete_context(session_id, f"file_{file_id}")
            
            if not vector_success:
                return {
                    "status": "error",
                    "message": "Failed to remove file from vector database"
                }

            return {
                "status": "success",
                "session_id": session_id,
                "file_id": file_id,
                "message": f"File removed from vector database context"
            }
        else:
            # Read context key from request body
            try:
                body = await request.json()
                key = body.get("key")
                
                if key:
                    # Remove the specific context key from vector database
                    vector_success = await session_service.delete_context(session_id, key)
                    
                    if not vector_success:
                        return {
                            "status": "error",
                            "message": "Failed to remove context from vector database"
                        }

                    return {
                        "status": "success",
                        "session_id": session_id,
                        "message": f"Context key '{key}' removed from vector database"
                    }
                else:
                    return {
                        "status": "error",
                        "message": "No key provided in request body"
                    }
            except Exception as e:
                return {
                    "status": "error",
                    "message": f"Failed to parse request body: {str(e)}"
                }

    except Exception as e:
        return {
            "status": "error",
            "message": f"Failed to remove context: {str(e)}"
        }
