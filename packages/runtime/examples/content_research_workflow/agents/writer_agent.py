"""
Writer Agent - Content creation and article writing.
"""

from examples.content_research_workflow.ai_models.huggingface_model import get_model
from examples.content_research_workflow.db import db
from examples.content_research_workflow.middlewares import InputContentSanitizer, OutputFormatter
from examples.content_research_workflow.tools.shared import read_article, word_count
from examples.content_research_workflow.tools.writer_agent import generate_outline, save_article
from framework.agents.agent import Agent
from framework.memory import AgentMemory


writer_agent = Agent(
    id="writer-agent",
    name="Writer Agent",
    description="Professional content writer specializing in creating engaging, well-structured articles",
    model=get_model(),
    instructions="""
You are a professional content writer specializing in creating engaging, well-structured articles.

Your responsibilities:
- Create article outlines based on topics
- Write clear, engaging content
- Count words and characters
- Save articles to files
- Read existing articles for reference

Focus on:
- Clear structure with headings
- Engaging introductions
- Well-organized body content
- Strong conclusions
- Appropriate tone for the audience
""",
    tools=[
        generate_outline,
        word_count,
        save_article,
        read_article,
    ],
    code_mode=False,
    storage=db,
    memory=AgentMemory(
        add_history_to_messages=True,
        num_history_responses=10,
    ),
    stream_enabled=True,
    input_middlewares=[InputContentSanitizer()],
    output_middlewares=[OutputFormatter()],
    temperature=0.8,  # Slightly higher for creativity
    max_tokens=4096,
)
