"""
Fact-Checker Agent - Fact verification and source validation.
"""

from examples.content_research_workflow.ai_models.huggingface_model import get_model
from examples.content_research_workflow.db import db
from examples.content_research_workflow.guardrails import ContentSafetyGuardrail
from examples.content_research_workflow.middlewares import InputContentSanitizer, OutputFormatter
from examples.content_research_workflow.tools.fact_checker_agent import (
    check_source_reliability,
    find_similar_claims,
    verify_fact,
)
from examples.content_research_workflow.tools.shared import web_search
from framework.agents.agent import Agent
from framework.memory import AgentMemory


fact_checker_agent = Agent(
    id="fact-checker-agent",
    name="Fact-Checker Agent",
    description="Fact-checking specialist focused on verifying information accuracy",
    model=get_model(),
    instructions="""
You are a fact-checking specialist focused on verifying information accuracy.

Your responsibilities:
- Verify factual claims
- Check source reliability
- Find similar claims from other sources
- Flag unverified or disputed information
- Provide evidence for verification

Guidelines:
- Never confirm unverified claims
- Always cite sources
- Flag potentially false information
- Be conservative - when in doubt, flag it
""",
    tools=[
        verify_fact,
        check_source_reliability,
        find_similar_claims,
        web_search,  # Additional search capability
    ],
    code_mode=False,
    storage=db,
    memory=AgentMemory(
        add_history_to_messages=True,
        window_size=20,
        num_history_responses=10,
    ),
    stream_enabled=False,  # Fact-checking needs complete response
    input_middlewares=[InputContentSanitizer()],
    output_middlewares=[
        OutputFormatter(),
        ContentSafetyGuardrail(strict_mode=True),
    ],
    temperature=0.3,  # Very low for accuracy
    max_tokens=2048,
)
