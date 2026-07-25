FROM python:3.11-slim

WORKDIR /app

# Create user early
RUN useradd -m mcp_user

COPY requirements.txt .

# Use BuildKit cache for pip
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install -r requirements.txt

# Copy with chown to preserve module path
COPY --chown=mcp_user:mcp_user . mcp_server/

USER mcp_user

EXPOSE 8000

CMD ["uvicorn", "mcp_server.server:app", "--host", "0.0.0.0", "--port", "8000"]
