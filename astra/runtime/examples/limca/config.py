"""Limca configuration loader.

Loads .limca/wiki.json for steerable wiki generation.
"""

import json
import os

from pydantic import BaseModel, Field, field_validator


class RepoNote(BaseModel):
    """A note providing context about the repository."""

    content: str = Field(description="Note content")
    author: str | None = Field(default=None, description="Note author")


class WikiPage(BaseModel):
    """A wiki page definition."""

    title: str = Field(description="Page title")
    purpose: str = Field(description="What this page should cover")
    parent: str | None = Field(default=None, description="Parent page title for hierarchy")
    files: list[str] | None = Field(default=None, description="Specific files to include")


class WikiConfig(BaseModel):
    """Configuration for wiki generation."""

    repo_notes: list[RepoNote] = Field(
        default_factory=list, description="Context notes about the repo"
    )
    pages: list[WikiPage] = Field(default_factory=list, description="Explicit page definitions")

    @field_validator("repo_notes")
    @classmethod
    def validate_repo_notes(cls, v: list[RepoNote]) -> list[RepoNote]:
        """Validate repo notes don't exceed limits."""
        for note in v:
            if len(note.content) > 10000:
                raise ValueError("Note content exceeds 10K character limit")
        return v

    @field_validator("pages")
    @classmethod
    def validate_pages(cls, v: list[WikiPage]) -> list[WikiPage]:
        """Validate pages don't exceed limits."""
        if len(v) > 30:
            raise ValueError("Cannot have more than 30 pages")

        # Check for unique titles
        titles = [p.title for p in v]
        if len(titles) != len(set(titles)):
            raise ValueError("Page titles must be unique")

        return v


class LimcaConfig(BaseModel):
    """Complete Limca configuration."""

    wiki: WikiConfig = Field(default_factory=WikiConfig, description="Wiki generation config")

    # Future: Add more config sections
    # indexer: IndexerConfig
    # embeddings: EmbeddingsConfig


def load_config(repo_path: str) -> LimcaConfig:
    """Load Limca configuration from a repository.

    Args:
        repo_path: Path to the repository root

    Returns:
        LimcaConfig with loaded settings (or defaults if no config found)
    """
    config_path = os.path.join(repo_path, ".limca", "wiki.json")

    if not os.path.exists(config_path):
        # Return default config if no file exists
        return LimcaConfig()

    with open(config_path) as f:
        data = json.load(f)

    # Parse wiki config
    wiki_config = WikiConfig(**data)
    return LimcaConfig(wiki=wiki_config)


def save_config(repo_path: str, config: LimcaConfig) -> None:
    """Save Limca configuration to a repository.

    Args:
        repo_path: Path to the repository root
        config: Configuration to save
    """
    config_dir = os.path.join(repo_path, ".limca")
    os.makedirs(config_dir, exist_ok=True)

    config_path = os.path.join(config_dir, "wiki.json")

    with open(config_path, "w") as f:
        json.dump(config.wiki.model_dump(), f, indent=2)


def get_page_hierarchy(config: WikiConfig) -> dict[str, list[str]]:
    """Get page hierarchy as parent -> children mapping.

    Args:
        config: Wiki configuration

    Returns:
        Dict mapping parent titles to list of child titles
    """
    hierarchy: dict[str, list[str]] = {"__root__": []}

    for page in config.pages:
        if page.parent is None:
            hierarchy["__root__"].append(page.title)
        else:
            if page.parent not in hierarchy:
                hierarchy[page.parent] = []
            hierarchy[page.parent].append(page.title)

    return hierarchy


def validate_hierarchy(config: WikiConfig) -> list[str]:
    """Validate page hierarchy for issues.

    Args:
        config: Wiki configuration

    Returns:
        List of validation error messages (empty if valid)
    """
    errors = []
    titles = {p.title for p in config.pages}

    for page in config.pages:
        if page.parent and page.parent not in titles:
            errors.append(f"Page '{page.title}' has unknown parent '{page.parent}'")

    # Check for cycles (simple check)
    for page in config.pages:
        seen = {page.title}
        current = page.parent
        while current:
            if current in seen:
                errors.append(f"Circular hierarchy detected involving '{page.title}'")
                break
            seen.add(current)
            parent_page = next((p for p in config.pages if p.title == current), None)
            current = parent_page.parent if parent_page else None

    return errors
