# Build stage
FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim AS builder
WORKDIR /app
COPY pyproject.toml .
RUN uv pip compile pyproject.toml > requirements.txt

# Runtime stage
FROM python:3.12-slim-bookworm
WORKDIR /app
COPY --from=builder /app/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY src/ .
CMD ["python", "-m", "app.main"]
