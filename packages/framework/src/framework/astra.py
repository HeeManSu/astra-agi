"""
Astra Framework - Main orchestrator class.

This module contains:
- FrameworkSettings: Configuration settings
- DependencyContainer: Dependency injection container
- Astra: Main orchestrator class
"""
from typing import TYPE_CHECKING, Any, Dict, List, Optional
from pydantic import ConfigDict, Field
from pydantic_settings import BaseSettings
from observability import Observability

# Using proper typing. Since Agent is imported locally to avoid circular imports, use TYPE_CHECKING for type hints. TODO: Refactor
if TYPE_CHECKING:
    from .agents.agent import Agent as AgentClass

class FrameworkSettings(BaseSettings):
    """Framework-level settings."""
    
    model_config = ConfigDict(env_file='.env', extra='allow')
    
    service_name: str = Field(default='astra', env='SERVICE_NAME')
    environment: str = Field(default='development', env='ENVIRONMENT')
    observability_log_file: Optional[str] = Field(default='./jsons/astra_observability.json', env='ASTRA_OBSERVABILITY_LOG_FILE')
    observability_log_level: str = Field(default='INFO', env='ASTRA_LOG_LEVEL')
    
    
class DependencyContainer:
    """Dependency injection container."""
    
    def __init__(self, observability: Optional[Observability] = None):
        self.observability = observability
        
        
class Astra:
    """
    The central orchestrator for Astra applications, managing agents and infrastructure.
    
    It is the main entry point for the framework.
    
    Example:
    ```python
      astra = Astra({
          'agents': [
              Agent(id="agent-1", name="Agent 1", instructions="...", model={...}),
              Agent(id="agent-2", name="Agent 2", instructions="...", model={...}),
              ...
          ]
      })
    ```
    """
    
    
    def __init__(self, config: Optional[Dict[str, Any]]  = None):
        """
        Initialize an Astra instance with the provided configuration.
        
        Args:
          config: Astra configurations (agents, memory, database, etc.)
        """
        
        if config is None: 
            raise ValueError("Config must be provided")
            
        agents = config.get('agents', [])
        
        self.settings = FrameworkSettings()
        self.dependencies = DependencyContainer()
        self._initialized = False
        
        # Initialize observability immediately in __init__ so logger is available
        # This ensures observability is ready before any logger access
        self.dependencies.observability = Observability.init(
            service_name=self.settings.service_name,
            log_level=self.settings.observability_log_level,
            enable_json_logs=True,
            log_file=self.settings.observability_log_file
        )
        
        # Logger will be initialized lazily when first accessed
        self._logger: Optional[Any] = None
        
        # Import Agent here to avoid circular import
        from .agents.agent import Agent as AgentClass
        
        # Store agents in a list to preserve order and allow easy iteration
        # Each agent has a unique id, retrieved via get_agent(id)
        self._agents: List[AgentClass] = []
        
        if agents:
            for agent in agents:
                self.add_agent(agent)
    
    @property
    def logger(self) -> Any:
        """
        Get logger instance from observability (lazy initialization).
        
        Returns:
          Logger instance from observability
        
        Note:
          Observability is initialized in __init__, so logger is always available.
        """
        if self._logger is None:
            if not self.dependencies.observability:
                raise RuntimeError("Observability is not initialized")
            self._logger = self.dependencies.observability.logger
        return self._logger
        
        
    def add_agent(self, agent: 'AgentClass') -> None:
        """
        Add a new agent to the Astra instance.
        
        This method allows dynamic registration of agents after the Astra instance
        has been created. The agent will be initialized with the current dependencies.
        
        Benefits of using a list:
        - Order preservation: agents maintain their registration order
        - Easy iteration: simple to loop through all agents
        - Dynamic modification: straightforward to append/remove agents at runtime
        - No key conflicts: each agent has a unique id
        
        Args:
            agent: Agent instance to add (must have a unique id)
        
        Raises:
            ValueError: If an agent with the same id already exists
        
        Note:
            When _register_astra() is helpful:
            - Agent created independently, then added to Astra: Links agent to Astra instance
            - Agent created with astra_instance param: Syncs dependencies even if _astra already set
            - Ensures unified observability: All agents share Astra's observability instance
            - Enables agent.get_astra_instance() to work correctly
            
            When it's NOT helpful:
            - Agent used standalone (never added to Astra): Not needed, agent works independently
            - If you want separate observability per agent: Rare case, usually not desired
        """    
        # Check if agent with this id already exists
        existing_agent = self._get_agent_by_id(agent.id)
        if existing_agent is not None:
            self.logger.info(
                f"Agent with id '{agent.id}' already exists. Skipping addition."
            )
            return
        
        # Register agent with this Astra instance
        # This is ALWAYS helpful when adding agent to Astra because:
        # 1. Sets agent._astra = self (links agent to Astra instance)
        # 2. Syncs agent.dependencies = self.dependencies (shares observability)
        # 3. Even if agent was created with astra_instance param, this ensures
        #    dependencies are synced and agent knows it's registered with this Astra
        # 4. Enables agent.get_astra_instance() to return the correct Astra instance
        #
        # When it's NOT helpful:
        # - If agent is never added to Astra (standalone usage) - but then this method
        #   is never called, so it's not an issue
        # - If you want agents to have separate observability (rare, usually not desired)
        agent._register_astra(self)
        
        # Append agent to list (preserves registration order)
        self._agents.append(agent)
        
        # Log successful addition
        self.logger.info(f"Added agent '{agent.id}'")
            
            
    def _get_agent_by_id(self, agent_id: str) -> Optional['AgentClass']:
        """
        Internal helper to find an agent by its id.
        
        Args:
            agent_id: The id of the agent to find
            
        Returns:
            Agent instance if found, None otherwise
        """
        for agent in self._agents:
            if agent.id == agent_id:
                return agent
        return None
    
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
        agent = self._get_agent_by_id(agent_id)
        if agent is None:
            available_ids = [a.id for a in self._agents]
            raise ValueError(
                f"Agent with id '{agent_id}' not found. "
                f"Available agents: {available_ids}"
            )
        return agent

    def list_agents(self) -> List['AgentClass']:
        """
        List all registered agents.
        
        Returns:
            List of all registered agents (preserves registration order)
        """
        return self._agents.copy()

    # async def startup(self) -> None:
    #     """
    #     Initialize framework components (async initialization).
        
    #     Observability is already initialized in __init__, so this method handles:
    #     - Initializing all registered agents
    #     - Any other async initialization tasks
        
    #     Example:
    #         ```python
    #         astra = Astra({'agents': [...]})  # Observability initialized here
    #         await astra.startup()  # Initialize agents and other async tasks
    #         ```
    #     """
    #     if self._initialized:
    #         return
        
    #     # Observability is already initialized in __init__
    #     # Initialize all registered agents
    #     for agent in self._agents:
    #         await agent.startup()
            
    #     self._initialized = True
    
    async def shutdown(self) -> None:
        """Cleanup framework components."""
        if self.dependencies.observability:
            self.dependencies.observability.shutdown()
            
        self._initialized = False
    

    def __repr__(self) -> str:
        """String representation of the Astra instance."""
        agent_count = len(self._agents)
        agent_ids = [agent.id for agent in self._agents]
        return f"Astra(agents={agent_count}, ids={agent_ids})"