"""
Editor Agent - Content editing and quality improvement.
"""

from examples.content_research_workflow.ai_models.huggingface_model import get_model
from examples.content_research_workflow.db import db
from examples.content_research_workflow.guardrails import ContentSafetyGuardrail
from examples.content_research_workflow.middlewares import InputContentSanitizer, OutputFormatter
from examples.content_research_workflow.tools.shared import (
    check_readability,
    read_article,
    word_count,
)
from framework.agents.agent import Agent
from framework.memory import AgentMemory


editor_agent = Agent(
    id="editor-agent",
    name="Editor Agent",
    description="Professional editor focused on improving content quality, grammar, and structure",
    model=get_model(),
    instructions="""
You are a professional editor focused on improving content quality.

Your responsibilities:
- Review articles for clarity and structure
- Improve grammar and style
- Check readability scores
- Ensure content meets quality standards
- Maintain consistent tone

Guidelines:
- Never add false information
- Preserve the author's voice
- Improve without changing meaning
- Flag content that violates guidelines
""",
    tools=[
        read_article,
        word_count,
        check_readability,
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
    output_middlewares=[
        OutputFormatter(),
        ContentSafetyGuardrail(strict_mode=False),
    ],
    temperature=0.5,  # Lower for more focused editing
    max_tokens=4096,
)
