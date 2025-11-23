"""
Astra Framework - Main orchestrator class.

This module contains:
- FrameworkSettings: Configuration settings
- DependencyContainer: Dependency injection container
- Astra: Main orchestrator class
"""
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Union
from pydantic import ConfigDict, Field
from pydantic_settings import BaseSettings
from observability import Observability

# Using proper typing. Since Agent is imported locally to avoid circular imports, use TYPE_CHECKING for type hints. TODO: Refactor
if TYPE_CHECKING:
    from .agents.agent import Agent as AgentClass

class FrameworkSettings(BaseSettings):
    """Framework-level settings."""
    
    model_config = ConfigDict(env_file='.env', extra='allow')  # type: ignore[assignment]
    
    service_name: str = Field(default='astra', validation_alias='SERVICE_NAME')
    environment: str = Field(default='development', validation_alias='ENVIRONMENT')
    observability_log_file: Optional[str] = Field(default='./jsons/astra_observability.json', validation_alias='ASTRA_OBSERVABILITY_LOG_FILE')
    observability_log_level: str = Field(default='INFO', validation_alias='ASTRA_LOG_LEVEL')
    
    
class AstraContext:
    """
    Infrastructure root for Astra applications.
    
    Holds shared resources like settings, observability, and logger.
    This context is injected into agents to provide them with the necessary infrastructure.
    """
    
    def __init__(self, settings: Optional[FrameworkSettings] = None):
        self.settings = settings or FrameworkSettings()
        
        # Initialize observability immediately
        self.observability = Observability.init(
            service_name=self.settings.service_name,
            log_level=self.settings.observability_log_level,
            enable_json_logs=True,
            log_file=self.settings.observability_log_file
        )
        
        # Logger initialized from observability
        self.logger = self.observability.logger
        
    def shutdown(self) -> None:
        """Shutdown infrastructure."""
        if self.observability:
            self.observability.shutdown()
        
        
class Astra:
    """
    Central orchestrator for managing agents and shared infrastructure.
    
    Provides dependency injection for agents, allowing them to share
    resources like observability, tools, storage, and knowledge bases.
    
    Example:
        ```python
        # Create agents
        agent1 = Agent(name="Researcher", model=Gemini("1.5-pro"))
        agent2 = Agent(name="Writer", model=Gemini("1.5-flash"))
        
        # Initialize Astra with shared resources
        astra = Astra(
            agents=[agent1, agent2],
            tools=[web_search],
            storage=postgres_db
        )
        ```
    """
    
    def __init__(
        self, 
        agents: Optional[List['AgentClass']] = None,
        tools: Optional[List[Any]] = None,
        storage: Optional[Any] = None,
        knowledge: Optional[Any] = None
    ):
        """
        Initialize Astra as a dependency injection container.
        
        Args:
            agents: List of Agent instances to manage
            tools: Global tools available to all managed agents
            storage: Global storage backend
            knowledge: Global knowledge base
        """
        
        # Create shared infrastructure (observability, logger, settings)
        self.context = AstraContext()
        self._initialized = False
        
        # Logger from context
        self._logger = self.context.logger
        
        # Global resources
        self.tools = tools or []
        self.storage = storage
        self.knowledge = knowledge
        
        # Import Agent here to avoid circular import
        from .agents.agent import Agent as AgentClass
        
        # Store agents in a dict for O(1) lookup
        self._agents: Dict[str, AgentClass] = {}
        
        # Register agents and inject context
        if agents: 
            for agent in agents:
                self.add_agent(agent)
                
    @property
    def logger(self) -> Any:
        """Get logger instance from context."""
        return self.context.logger
    
    def add_tool(self, tool: Any) -> None: 
        """
        Add a global tool available to all managed agents.
        
        Args:
            tool: Tool function or object
        """
        
        self.tools.append(tool)
        
        #Propagate to existing agents
        for agent in self._agents.values():
            agent.add_tool(tool)
            
    def set_storage(self, storage: Any) -> None:
        """
        Set global storage backend.
        
        Args:
            storage: Storage backend instance
        """
        
        self.storage = storage
        # Propagate to existing agents that dont have their own storage
        for agent in self._agents.values():
            if not agent.storage:
                agent.set_storage(storage)
                
    def set_knowledge(self, knowledge: Any) -> None:
        """
        Set global knowledge base.
        
        Args:
            knowledge: Knowledge base instance
        """
        self.knowledge = knowledge
        # Propagate to existing agents that don't have their own knowledge
        for agent in self._agents.values():
            if not agent.knowledge:
                agent.set_knowledge(knowledge)
                
                
    def add_agent(self, agent: 'AgentClass') -> None:
        """
        Register an agent and inject shared context (Dependency Injection).
        
        This method:
        - Adds agent to registry for lookup
        - Injects shared AstraContext into agent
        - Injects global tools, storage, and knowledge (if agent lacks them)
        - Does NOT initialize the agent (agents self-initialize on first use)
        
        Args:
            agent: Agent instance to register (must have unique id)
        """
        # Check if agent already exists
        if agent.id in self._agents:
            self._logger.info(f"Agent with id '{agent.id}' already exists. Skipping addition.")
            return
        
        # Inject shared context (Dependency Injection)
        agent.set_context(self.context)
        
        # Inject global tools, storage, and knowledge (if agent lacks them)
        if self.tools:
            for tool in self.tools: 
                agent.add_tool(tool)
                
        if self.storage and not agent.storage:
            agent.set_storage(self.storage)
            
        if self.knowledge and not agent.knowledge:
            agent.set_knowledge(self.knowledge)
            
        # Add agent to registry (preserves insertion order)
        self._agents[agent.id] = agent
        
        # Log successful addition
        self._logger.info(f"Added agent '{agent.id}'")
        
    def get_agent(self, agent_id: str) -> 'AgentClass':
        """
        Retrieve a registered agent by its id.
        
        Args:
            agent_id: The id of the agent to retrieve
            
        Returns:
            Agent instance with the matching id
            
        Raises:
            ValueError: If no agent with the given id is found
        """
        
        agent = self._agents.get(agent_id)
        if agent is None:
            available_ids = list(self._agents.keys())
            raise ValueError(
                f"Agent with id '{agent_id}' not found. "
                f"Available agents: {available_ids}"
            )
        return agent
        
    def list_agents(self) -> List['AgentClass']:
        """
        List all registered agents.
        
        Returns:
            List of all registered agents (preserves insertion order)
        """
        return list(self._agents.values())
    
    async def shutdown(self) -> None:
        """Cleanup framework components."""
        if self.context:
            self.context.shutdown()
            
        self._initialized = False
            
    def __repr__(self) -> str:
        """String representation of the Astra instance."""
        agent_count = len(self._agents)
        agent_ids = list(self._agents.keys())
        return f"Astra(agents={agent_count}, ids={agent_ids})"
        