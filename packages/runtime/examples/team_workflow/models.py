"""
Model Configuration for Team Workflow.
"""

from astra import Gemini


def get_model():
    """Get the AI model instance for agents."""
    # Use Gemini-2.5-Flash as requested
    return Gemini(model_id="gemini-2.5-flash")
