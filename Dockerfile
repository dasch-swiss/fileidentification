FROM python:3.12-slim-trixie AS py_env
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/
RUN apt-get update && apt-get install -y golang

WORKDIR /app
COPY . .
RUN uv sync --no-group dev

FROM python:3.12-slim-trixie

# Set environment variables to prevent interactive prompts
ENV DEBIAN_FRONTEND=noninteractive
ENV TZ=UTC

# Update package lists and install system dependencies
RUN apt-get update && apt-get install -y \
    ffmpeg \
    imagemagick \
    ghostscript \
    libreoffice-nogui \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY --from=py_env /app/.venv /app/.venv

# copy the app
COPY ./fileidentification /app/fileidentification
COPY ./identify.py /app/.
COPY .env /app/.

ENTRYPOINT ["/app/.venv/bin/python3", "/app/identify.py"]
