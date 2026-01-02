"""Feature Registry - Declarative feature definitions."""

FEATURES = {
    # ========================================
    # CORE (always included)
    # ========================================
    "core": {
        "always": True,
        "files": [
            "app/main.py.j2",
            "app/settings.py.j2",
            "app/api/__init__.py.j2",
            "app/api/router.py.j2",
            "app/api/agents.py.j2",
            "app/api/admin.py.j2",
            "app/agents/__init__.py.j2",
            "app/agents/welcome_agent.py.j2",
            "pyproject.toml.j2",
            ".env.example.j2",
            "README.md.j2",
        ],
        "deps": [],
    },
    # ========================================
    # AUTH OPTIONS
    # ========================================
    "auth-none": {
        "files": [],
        "deps": [],
    },
    "auth-api-key": {
        "files": [
            "app/auth/__init__.py.j2",
            "app/auth/api_key.py.j2",
        ],
        "deps": [],
        "conflicts": ["auth-jwt"],
    },
    "auth-jwt": {
        "files": [
            "app/auth/__init__.py.j2",
            "app/auth/jwt.py.j2",
        ],
        "deps": ["python-jose[cryptography]>=3.3.0"],
        "conflicts": ["auth-api-key"],
    },
    # ========================================
    # MIDDLEWARE
    # ========================================
    "rate-limit": {
        "files": [
            "app/middleware/__init__.py.j2",
            "app/middleware/rate_limit.py.j2",
        ],
        "deps": ["slowapi>=0.1.9"],
    },
}
