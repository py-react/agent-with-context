"""
Workflow Factory for managing workflow dependencies and ensuring proper layering
"""
import time
from typing import List
from langchain_core.tools import BaseTool
from render_relay.utils.get_logger import get_logger

from ..workflow.agent_workflow import AgentWorkflow
from ..workflow.langgraph_workflow import LangGraphWorkflowService

logger = get_logger("workflow_factory")

class WorkflowFactory:
    """Factory for creating and managing workflow dependencies"""
    
    def __init__(self):
        self._workflows = {}
        self._initialized = False
        self._service_factory = None
    
    def set_service_factory(self, service_factory):
        """Set the service factory for dependency injection"""
        self._service_factory = service_factory
    
    def initialize_workflows(self, tools: List[BaseTool] = None):
        """Initialize all workflows with proper dependencies"""
        start_time = time.time()
        logger.info("🏭 WorkflowFactory.initialize_workflows started")
        
        if self._initialized:
            logger.debug("✅ Workflows already initialized, skipping")
            return
        
        if not self._service_factory:
            raise RuntimeError("Service factory not set. Call set_service_factory() first.")
        
        # Create LangGraph workflow service with tools
        langgraph_start = time.time()
        logger.debug("🔧 Creating LangGraph workflow service...")
        self._workflows['langgraph'] = LangGraphWorkflowService(tools=tools)
        langgraph_time = time.time() - langgraph_start
        logger.debug(f"✅ LangGraph workflow service created in {langgraph_time:.3f}s")
        
        # Create agent workflow with injected dependencies using session service
        agent_start = time.time()
        logger.debug("🔧 Creating agent workflow with session service...")
        self._workflows['agent'] = AgentWorkflow(
            session_service=self._service_factory.get_service('session'),
            langgraph_workflow_service=self._workflows['langgraph']
        )
        agent_time = time.time() - agent_start
        logger.debug(f"✅ Agent workflow created in {agent_time:.3f}s")
        
        self._initialized = True
        total_time = time.time() - start_time
        logger.info(f"🎉 WorkflowFactory.initialize_workflows completed in {total_time:.3f}s (langgraph: {langgraph_time:.3f}s, agent: {agent_time:.3f}s)")
    
    def update_tools(self, tools: List[BaseTool]):
        """Update tools for workflows that need them"""
        if 'langgraph' in self._workflows:
            self._workflows['langgraph'].set_tools(tools)
    
    def get_workflow(self, workflow_name: str):
        """Get a workflow by name"""
        if not self._initialized:
            raise RuntimeError("Workflows not initialized. Call initialize_workflows() first.")
        
        if workflow_name not in self._workflows:
            raise ValueError(f"Workflow '{workflow_name}' not found")
        
        return self._workflows[workflow_name]
    
    def get_all_workflows(self):
        """Get all workflows"""
        if not self._initialized:
            raise RuntimeError("Workflows not initialized. Call initialize_workflows() first.")
        
        return self._workflows.copy()
    
    def get_agent_workflow(self) -> AgentWorkflow:
        """Get the agent workflow"""
        return self.get_workflow('agent')
    
    def get_langgraph_workflow(self) -> LangGraphWorkflowService:
        """Get the LangGraph workflow service"""
        return self.get_workflow('langgraph')

# Global workflow factory instance
workflow_factory = WorkflowFactory() 