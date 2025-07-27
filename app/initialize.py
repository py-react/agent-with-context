"""
Initialization module for setting up the application with proper layering
"""
import time
import asyncio
from typing import List, Optional
from langchain_core.tools import BaseTool
from render_relay.utils.get_logger import get_logger

from .factory.service_factory import service_factory
from .factory.workflow_factory import workflow_factory
from .factory.tool_factory import ToolFactory

logger = get_logger("initialize")

async def initialize_application():
    """Initialize the application with proper service dependencies"""
    start_time = time.time()
    logger.info("🚀 Starting application initialization...")
    
    # Initialize tool factory
    tools_start = time.time()
    logger.debug("🔧 Initializing tool factory...")
    tool_factory = ToolFactory()
    tools = tool_factory.get_tools()
    tools_time = time.time() - tools_start
    logger.debug(f"✅ Tool factory initialized in {tools_time:.3f}s")
    
    # Initialize services with tools
    services_start = time.time()
    logger.debug("🏭 Initializing services...")
    service_factory.initialize_services(tools=tools)
    services_time = time.time() - services_start
    logger.debug(f"✅ Services initialized in {services_time:.3f}s")
    
    # Note: Tools now use service factory directly, no need to update services manually
    update_start = time.time()
    logger.debug("🔄 Tools are ready (using service factory directly)...")
    update_time = time.time() - update_start
    logger.debug(f"✅ Tools ready in {update_time:.3f}s")
    
    # Update services with the tools
    update_services_start = time.time()
    logger.debug("🔄 Updating services with tools...")
    service_factory.update_tools(tools)
    update_services_time = time.time() - update_services_start
    logger.debug(f"✅ Services updated in {update_services_time:.3f}s")
    
    # Initialize workflows
    workflow_start = time.time()
    logger.debug("🔧 Initializing workflows...")
    workflow_factory.set_service_factory(service_factory)
    workflow_factory.initialize_workflows(tools=tools)
    workflow_time = time.time() - workflow_start
    logger.debug(f"✅ Workflows initialized in {workflow_time:.3f}s")
    
    # Initialize async services
    async_start = time.time()
    logger.debug("⚡ Initializing async services...")
    await service_factory.initialize_async_services()
    async_time = time.time() - async_start
    logger.debug(f"✅ Async services initialized in {async_time:.3f}s")
    
    total_time = time.time() - start_time
    logger.info(f"Application initialization completed successfully in {total_time:.3f}s (tools: {tools_time:.3f}s, services: {services_time:.3f}s, update: {update_time:.3f}s, update_services: {update_services_time:.3f}s, async: {async_time:.3f}s)")
    logger.info("Application initialized successfully")
    return service_factory

async def cleanup_application():
    """Cleanup application resources - delegates to ServiceFactory"""
    logger.info("🧹 Starting application cleanup...")
    await service_factory.cleanup_services()
    logger.info("✅ Application cleanup completed")

def get_all_services():
    """Get all services"""
    if not service_factory._initialized:
        raise RuntimeError("Application not initialized. Please wait for the application to start up completely.")
    return service_factory.get_all_services()

def get_service(service_name: str):
    """Get a service by name"""
    if not service_factory._initialized:
        raise RuntimeError("Application not initialized. Please wait for the application to start up completely.")
    return service_factory.get_service(service_name)

def get_service_factory():
    """Get the service factory instance"""
    if not service_factory._initialized:
        raise RuntimeError("Application not initialized. Please wait for the application to start up completely.")
    return service_factory

def get_workflow_factory():
    """Get the workflow factory instance"""
    if not service_factory._initialized:
        raise RuntimeError("Application not initialized. Please wait for the application to start up completely.")
    return workflow_factory

def get_tool_factory():
    """Get the tool factory instance"""
    return ToolFactory() 