# Use a Python image with uv pre-installed
FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim

# Install the project into `/app`
WORKDIR /app

# Enable bytecode compilation
ENV UV_COMPILE_BYTECODE=1

# Copy from the cache instead of linking since it's a mounted volume
ENV UV_LINK_MODE=copy

# Copy the project definition
# COPY pyproject.toml /app/

# Install the project's dependencies using the lockfile and settings
# RUN --mount=type=cache,target=/root/.cache/uv \
#     --mount=type=bind,source=uv.lock,target=uv.lock \
#     --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
#     uv sync --frozen --no-install-project --no-dev

# Copy the project
COPY . /app

# Install dependencies (without lockfile for template simplicity, in prod use uv.lock)
RUN --mount=type=cache,target=/root/.cache/uv \
    uv pip install -r <(uv pip compile pyproject.toml)

# Place executables in the environment at the front of the path
# ENV PATH="/app/.venv/bin:$PATH"

# Reset the entrypoint, don't invoke `uv`
ENTRYPOINT []

# Run the application
CMD ["uv", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
