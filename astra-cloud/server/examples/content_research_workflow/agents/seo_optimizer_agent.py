"""
SEO Optimizer Agent - SEO optimization and analysis.
"""

from examples.content_research_workflow.ai_models.huggingface_model import get_model
from examples.content_research_workflow.db import db
from examples.content_research_workflow.middlewares import (
    InputContentSanitizer,
    OutputFormatter,
    SEOValidator,
)
from examples.content_research_workflow.tools.seo_optimizer_agent import (
    analyze_keywords,
    generate_chart,
    generate_meta_description,
    optimize_headings,
)
from examples.content_research_workflow.tools.shared import check_readability, read_article
from framework.agents.agent import Agent
from framework.memory import AgentMemory


seo_optimizer_agent = Agent(
    id="seo-optimizer-agent",
    name="SEO Optimizer Agent",
    description="SEO specialist focused on optimizing content for search engines",
    model=get_model(),
    instructions="""
You are an SEO specialist focused on optimizing content for search engines.

Your responsibilities:
- Analyze keywords in content
- Generate meta descriptions
- Optimize headings structure
- Generate data visualizations (charts)
- Improve SEO metrics

Guidelines:
- Focus on natural keyword integration
- Ensure readability is maintained
- Create compelling meta descriptions
- Use data visualizations to enhance content
- Balance SEO with user experience
""",
    tools=[
        analyze_keywords,
        generate_meta_description,
        optimize_headings,
        generate_chart,
        read_article,
        check_readability,
    ],
    code_mode=True,  # Enabled for chart generation
    storage=db,
    memory=AgentMemory(
        add_history_to_messages=True,
        num_history_responses=10,
    ),
    stream_enabled=True,
    input_middlewares=[InputContentSanitizer()],
    output_middlewares=[OutputFormatter(), SEOValidator()],
    temperature=0.7,
    max_tokens=2048,
)
