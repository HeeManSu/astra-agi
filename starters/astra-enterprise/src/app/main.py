import logging

from app.agents.finance_agent import finance_agent
from app.agents.research_agent import research_agent
from app.core.settings import settings
from astra.server import create_app


# Configure logging
logging.basicConfig(level=settings.LOG_LEVEL)
logger = logging.getLogger(__name__)

# Register agents
agents = {
    "finance": finance_agent,
    "research": research_agent,
}

# Create application
app = create_app(
    agents=agents,
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
)

if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", host=settings.HOST, port=settings.PORT, reload=True)
