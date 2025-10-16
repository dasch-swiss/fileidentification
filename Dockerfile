FROM python:3.12-slim-trixie AS py_env

# installing the py env, pygfried needs golang but just for installing
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/
RUN apt-get update && apt-get install -y golang

WORKDIR /app
COPY . .
RUN uv sync --no-group dev

FROM python:3.12-slim-trixie

# Set environment variables to prevent interactive prompts
ENV DEBIAN_FRONTEND=noninteractive
ENV TZ=UTC

# install the programs
RUN apt-get update && apt-get install --no-install-recommends -y \
    ffmpeg \
    imagemagick \
    ghostscript \
    libreoffice-nogui \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# add the py env
COPY --from=py_env /app/.venv /app/.venv

# copy the app
COPY ./fileidentification /app/fileidentification
COPY ./identify.py /app/.
COPY ./appconfig.toml /app/.

ENTRYPOINT ["/app/.venv/bin/python3", "/app/identify.py"]
