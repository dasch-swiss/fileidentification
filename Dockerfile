FROM ubuntu:22.04

# Set environment variables to prevent interactive prompts
ENV DEBIAN_FRONTEND=noninteractive
ENV TZ=UTC

# Update package lists and install system dependencies
RUN apt-get update && apt-get install -y \
    # Basic utilities
    curl \
    wget \
    ca-certificates \
    # Media processing tools
    ffmpeg \
    imagemagick \
    ghostscript \
    inkscape \
    # LibreOffice for document conversion
    libreoffice \
    # Additional dependencies for media tools
    libmagickwand-dev \
    && rm -rf /var/lib/apt/lists/*

# Install Siegfried
RUN wget -qO - https://keybase.io/richardlehane/pgp_keys.asc | apt-key add - \
    && echo 'deb https://github.com/richardlehane/siegfried/releases/download/v1.10.0/ ./' | tee /etc/apt/sources.list.d/siegfried.list \
    && apt-get update \
    && apt-get install -y siegfried \
    && rm -rf /var/lib/apt/lists/*

# Install UV package manager
RUN curl -LsSf https://astral.sh/uv/install.sh | sh
ENV PATH="/root/.local/bin:$PATH"

# Set working directory
WORKDIR /app

# Copy application files
COPY . .

# Create a non-root user for running the application
RUN useradd -m -u 1000 fileident && \
    chown -R fileident:fileident /app

USER fileident

# Expose any necessary ports (if the app serves HTTP, adjust as needed)
# EXPOSE 8000

# Default command
CMD ["uv", "run", "identify.py", "--help"]