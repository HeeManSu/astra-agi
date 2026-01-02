"""Feature Engine - Registry lookup and change planning."""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from astra_cli.templates.registry import FEATURES


# Features that cannot be removed
PROTECTED_FEATURES = {"core"}


@dataclass
class FeaturePlan:
    """Plan for adding/removing a feature."""

    files_to_add: list[str] = field(default_factory=list)
    files_to_remove: list[str] = field(default_factory=list)
    deps_to_add: list[str] = field(default_factory=list)
    deps_to_remove: list[str] = field(default_factory=list)
    state_updates: dict[str, Any] = field(default_factory=dict)
    conflicts: list[str] = field(default_factory=list)


def validate_feature(feature: str) -> str | None:
    """
    Validate that a feature exists in the registry.

    Args:
        feature: Feature key to validate

    Returns:
        Error message if invalid, None if valid
    """
    feature_key = feature.replace(" ", "-")

    if feature_key in FEATURES:
        return None

    # Check for auth-* pattern
    if feature_key.startswith("auth-"):
        auth_type = feature_key.replace("auth-", "")
        if f"auth-{auth_type}" in FEATURES:
            return None

    valid_features = [
        k for k in FEATURES.keys() if not k.startswith("auth-") or k == "auth-api-key"
    ]
    return f"Unknown feature '{feature}'. Valid features: {', '.join(sorted(valid_features))}"


def get_feature_plan(config: dict[str, Any]) -> FeaturePlan:
    """
    Generate a plan for initial project creation based on config.

    Args:
        config: Project config

    Returns:
        FeaturePlan with all files and deps needed
    """
    plan = FeaturePlan()
    features = config.get("features", {})

    # Always include core
    core_feature = FEATURES.get("core", {})
    plan.files_to_add.extend(core_feature.get("files", []))
    plan.deps_to_add.extend(core_feature.get("deps", []))

    # Add auth feature if specified
    auth_type = features.get("auth")
    if auth_type and auth_type != "none":
        auth_key = f"auth-{auth_type}"
        if auth_key in FEATURES:
            auth_feature = FEATURES[auth_key]
            plan.files_to_add.extend(auth_feature.get("files", []))
            plan.deps_to_add.extend(auth_feature.get("deps", []))

    # Add other features
    for feature_key, enabled in features.items():
        if feature_key in ("core", "auth") or not enabled:
            continue
        if feature_key in FEATURES:
            feature = FEATURES[feature_key]
            plan.files_to_add.extend(feature.get("files", []))
            plan.deps_to_add.extend(feature.get("deps", []))

    return plan


def get_add_feature_plan(config: dict[str, Any], feature_key: str) -> FeaturePlan:
    """
    Generate a plan for adding a single feature.

    Args:
        config: Current project config
        feature_key: Feature to add

    Returns:
        FeaturePlan with files and deps to add
    """
    plan = FeaturePlan()

    if feature_key not in FEATURES:
        return plan

    feature = FEATURES[feature_key]
    plan.files_to_add = feature.get("files", [])
    plan.deps_to_add = feature.get("deps", [])

    # Check for conflicts
    conflicts = feature.get("conflicts", [])
    current_features = config.get("features", {})

    for conflict in conflicts:
        if conflict in current_features:
            plan.conflicts.append(conflict)

    return plan


def get_remove_feature_plan(config: dict[str, Any], feature_key: str) -> FeaturePlan:
    """
    Generate a plan for removing a feature.

    Args:
        config: Current project config
        feature_key: Feature to remove

    Returns:
        FeaturePlan with files and deps to remove
    """
    plan = FeaturePlan()

    if feature_key not in FEATURES:
        return plan

    feature = FEATURES[feature_key]

    # Files to remove (strip .j2 extension)
    plan.files_to_remove = [f.replace(".j2", "") for f in feature.get("files", [])]

    # Deps to remove (only if not used by other features)
    deps = set(feature.get("deps", []))
    current_features = config.get("features", {})

    for other_key, enabled in current_features.items():
        if other_key == feature_key or not enabled:
            continue
        if other_key in FEATURES:
            other_deps = set(FEATURES[other_key].get("deps", []))
            deps -= other_deps  # Keep deps used by other features

    plan.deps_to_remove = list(deps)

    return plan


def validate_features_in_config(config: dict[str, Any]) -> list[str]:
    """
    Validate all features in config exist in registry.

    Args:
        config: Project config

    Returns:
        List of validation error messages
    """
    errors = []
    features = config.get("features", {})
    if features is None:
        features = {}

    for feature_key, value in features.items():
        if feature_key == "core":
            continue
        if feature_key == "auth":
            # Auth is stored as auth: "jwt" not auth-jwt: true
            if value and value != "none":
                auth_key = f"auth-{value}"
                if auth_key not in FEATURES:
                    errors.append(f"Unknown auth type '{value}'")
        elif feature_key not in FEATURES:
            errors.append(f"Unknown feature '{feature_key}'")

    return errors


def get_sync_plan(config: dict[str, Any], project_path: Path) -> FeaturePlan:
    """
    Generate a plan to sync project - add missing files only.

    Args:
        config: Project config
        project_path: Path to project root

    Returns:
        FeaturePlan with files to add
    """
    plan = FeaturePlan()
    features = config.get("features", {})

    # Collect all expected files
    expected_files: list[str] = []

    # Core files
    core_feature = FEATURES.get("core", {})
    expected_files.extend(core_feature.get("files", []))

    # Auth feature
    auth_type = features.get("auth")
    if auth_type and auth_type != "none":
        auth_key = f"auth-{auth_type}"
        if auth_key in FEATURES:
            expected_files.extend(FEATURES[auth_key].get("files", []))

    # Other features
    for feature_key, enabled in features.items():
        if feature_key in ("core", "auth") or not enabled:
            continue
        if feature_key in FEATURES:
            expected_files.extend(FEATURES[feature_key].get("files", []))

    # Check which files are missing
    for template_file in expected_files:
        output_file = template_file.replace(".j2", "")
        output_path = Path(project_path) / output_file
        if not output_path.exists():
            plan.files_to_add.append(template_file)

    return plan
