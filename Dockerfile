# syntax=docker/dockerfile:1
#
# One image, two entrypoints. The container command selects the process:
#   docker run beacon:<sha> api        # serves the HTTP API on :8000
#   docker run beacon:<sha> checker    # runs the probe loop
#
# Multi-stage: the build stage has uv and resolves the venv; the runtime stage carries
# only Python and the venv — no uv, no build tooling.

# ---- build ---------------------------------------------------------------------
FROM python:3.12-slim-bookworm AS build

# Pinned uv, copied in rather than installed — reproducible and no network beyond the base.
COPY --from=ghcr.io/astral-sh/uv:0.11.28 /uv /uvx /bin/

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=0

WORKDIR /app

# Dependencies first, as their own layer — rebuilt only when the lockfile changes.
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --frozen --no-install-project --no-dev

# Then the application itself.
COPY beacon/ ./beacon/
COPY pyproject.toml uv.lock README.md ./
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev

# ---- runtime ------------------------------------------------------------------
FROM python:3.12-slim-bookworm AS runtime

# Run as a non-root user.
RUN groupadd --system beacon && useradd --system --gid beacon --create-home --home-dir /app beacon

WORKDIR /app
COPY --from=build --chown=beacon:beacon /app /app

ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    BEACON_HOST=0.0.0.0 \
    BEACON_PORT=8000

USER beacon

# Documents the api port; the checker publishes nothing.
EXPOSE 8000

ENTRYPOINT ["python", "-m", "beacon"]
CMD ["api"]
