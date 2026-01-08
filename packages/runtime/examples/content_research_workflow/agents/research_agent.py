"""
Research Agent - Web research and information gathering.
"""

from examples.content_research_workflow.ai_models.huggingface_model import get_model
from examples.content_research_workflow.db import db
from examples.content_research_workflow.middlewares import InputContentSanitizer, OutputFormatter
from examples.content_research_workflow.tools.research_agent import (
    extract_key_points,
    get_recent_news,
    scrape_url,
    web_search,
)
from framework.agents.agent import Agent
from framework.memory import AgentMemory


research_agent = Agent(
    id="research-agent",
    name="Research Agent",
    description="Specialized agent for gathering comprehensive information from web sources",
    model=get_model(),
    instructions="""
You are a research specialist focused on gathering accurate, comprehensive information.

Your responsibilities:
- Search the web for relevant information
- Scrape and extract key points from articles
- Gather recent news on topics
- Organize findings clearly
- Cite sources for all information

Always verify information from multiple sources when possible.
""",
    tools=[
        web_search,
        scrape_url,
        extract_key_points,
        get_recent_news,
    ],
    code_mode=False,
    storage=db,
    memory=AgentMemory(
        add_history_to_messages=True,
        window_size=20,
        num_history_responses=10,
    ),
    stream_enabled=True,
    input_middlewares=[InputContentSanitizer()],
    output_middlewares=[OutputFormatter()],
    temperature=0.7,
    max_tokens=2048,
)
