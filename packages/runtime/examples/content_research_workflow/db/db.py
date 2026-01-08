"""
Database Configuration.

Shared MongoDB storage instance for all agents.
"""

import os

from framework.storage.databases.mongodb import MongoDBStorage


def get_storage():
    """
    Get shared MongoDB storage instance.

    Returns:
        MongoDBStorage instance
    """
    mongo_url = os.getenv("MONGODB_URL", "mongodb://localhost:27017")
    return MongoDBStorage(
        url=mongo_url,
        db_name="content_research_workflow",
    )


# Shared storage instance
db = get_storage()
