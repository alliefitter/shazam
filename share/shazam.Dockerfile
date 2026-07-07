FROM python:3.14-slim AS builder

ENV \
  # Don't create .pyc files, these aren't useful in a container imager
  PYTHONDONTWRITEBYTECODE=1 \
  # Immediately write to stdout and stderr instead of buffering the output
  PYTHONUNBUFFERED=1 \
  # Dump tracebacks when non-python code crashes, useful for diagnosing issues
  PYTHONFAULTHANDLER=1 \
  UV_UNMANAGED_INSTALL="/opt/uv/bin" \
  PATH="/opt/uv/bin:${PATH}"


# Setup a venv and install uv

RUN apt-get update && \
    apt-get install -y --no-install-recommends curl && \
    rm -rf /var/lib/apt/lists/* && \
    curl -LsSf https://astral.sh/uv/install.sh | sh

WORKDIR /app

# Copy in just the files needed for installing dependencies, and install
# them in a layer that can be cached independently of the app source
COPY ./pyproject.toml ./uv.lock ./

RUN uv sync --no-install-project

COPY ./alembic.ini .
COPY ./src ./src
COPY ./bin ./bin

# Now that the source is present, install the local project itself
RUN uv sync

FROM python:3.14-slim AS production

ENV \
  # Don't create .pyc files, these aren't useful in a container imager
  PYTHONDONTWRITEBYTECODE=1 \
  # Immediately write to stdout and stderr instead of buffering the output
  PYTHONUNBUFFERED=1 \
  # Dump tracebacks when non-python code crashes, useful for diagnosing issues
  PYTHONFAULTHANDLER=1 \
  # Trust proxy headers such as `X-Forwarded-For`, the default is to only trust headers from 127.0.0.1
  FORWARDED_ALLOW_IPS="*" \
  # Add the app venv to $PATH
  PATH="/app/.venv/bin:${PATH}"

WORKDIR /app

# libx11-6/libxext6 are needed by Tk (not python-xlib, which is pure Python)
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
      python3-tk libportaudio2 libasound2 libx11-6 libxext6 && \
    rm -rf /var/lib/apt/lists/*

COPY --from=builder /app .

# Switch to app user
USER app


ENTRYPOINT ["./bin/entrypoint.sh"]
