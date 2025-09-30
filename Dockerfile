FROM debian:stable-slim

# Set environment variables to prevent interactive prompts
ENV DEBIAN_FRONTEND=noninteractive
ENV TZ=UTC

# Update package lists and install system dependencies
RUN apt-get update && apt-get install -y \
    ffmpeg \
    imagemagick \
    ghostscript \
    libreoffice \
    golang \
    python3-pip \
    python3-venv \
    && rm -rf /var/lib/apt/lists/*


WORKDIR /app

# for some reason, pygfried fails installing with uv
COPY ./requirements.txt /app/requirements.txt
RUN python3 -m venv /app/.venv && /app/.venv/bin/pip3 install --no-cache-dir --upgrade -r /app/requirements.txt

# copy the app
COPY ./fileidentification /app/fileidentification
COPY ./identify.py /app/.
COPY .env /app/.
