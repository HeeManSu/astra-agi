"""
HuggingFace Model Configuration.

Supports both local and remote HuggingFace models.
"""

import os

from framework.models.huggingface.local import HuggingFaceLocal
from framework.models.huggingface.remote import HuggingFaceRemote


def get_model():
    """
    Get model instance - prefers remote if URL is set, otherwise local.

    Returns:
        Model instance (HuggingFaceRemote or HuggingFaceLocal)
    """
    remote_url = os.getenv("HUGGINGFACE_REMOTE_URL")
    if remote_url:
        return HuggingFaceRemote(base_url=remote_url)
    else:
        # Use local model - smaller model for testing
        model_id = os.getenv("MODEL_ID", "Qwen/Qwen2.5-1.5B-Instruct")
        return HuggingFaceLocal(model_id)
