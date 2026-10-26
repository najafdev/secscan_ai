# SecScan AI configuration file
FROM kalilinux/kali-rolling

# Set environment variables
ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1

# Update and install basic tools
RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    libldap2-dev \
    libsasl2-dev \
    libssl-dev \
    portaudio19-dev \
    git \
    curl \
    wget \
    sudo \
    && rm -rf /var/lib/apt/lists/*

# Create working directory
WORKDIR /secscan_ai

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip3 install -r requirements.txt --break-system-packages

# Copy the rest of the application. .dockerignore excludes local credentials,
# generated reports, caches and other host-only state from the build context.
COPY . .

# Preserve the full host installer while using its deterministic container mode here.
# Container builds must not upgrade the base distribution, run a background model
# daemon, fetch a model, or create host-style global command links.
RUN chmod +x install.sh && SECSCAN_AI_INSTALL_CONTEXT=container ./install.sh

# Keep both the historical external report path and the application-local runtime dirs.
RUN mkdir -p /reports /secscan_ai/reports /secscan_ai/logs /secscan_ai/templates /secscan_ai/database/migrations \
    && chmod 755 /reports /secscan_ai/reports /secscan_ai/logs /secscan_ai/templates /secscan_ai/database/migrations

# Expose web dashboard port
EXPOSE 5000

# Set entry point
ENTRYPOINT ["python3", "advance_secscan_ai.py"]
