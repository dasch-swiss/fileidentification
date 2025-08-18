FROM ubuntu:22.04

# Set environment variables to prevent interactive prompts
ENV DEBIAN_FRONTEND=noninteractive
ENV TZ=UTC

# Update package lists and install system dependencies
RUN apt-get update && apt-get install -y \
    # Basic utilities
    curl \
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
RUN curl -L https://github.com/richardlehane/siegfried/releases/latest/download/siegfried_1.11.2_linux_amd64.deb -o siegfried.deb \
    && dpkg -i siegfried.deb \
    && rm siegfried.deb \
    && sf -update


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

# Default command
CMD ["uv", "run", "identify.py", "--help"]