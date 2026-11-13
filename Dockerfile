# SPDX-FileCopyrightText: Copyright (c) 2026 Thế Vị (@TeeVee98). All rights reserved.
# SPDX-License-Identifier: MIT
# Project: Synapse-Hub (https://github.com/TeeVee98/Synapse-Hub)

# Enterprise All-in-One QA Container Image
# Provides complete runtimes for Python 3.12, Node.js 20, OpenJDK Headless,
# Chromium Headless & Playwright dependencies, and Synapse-Hub CLI.

FROM python:3.12-slim-bookworm@sha256:935c3c5b12357a7e10caa9c1e6ca5692344d97cf229832ef584be2cec9fc03df

LABEL org.opencontainers.image.title="Synapse-Hub Enterprise QA" \
      org.opencontainers.image.description="Enterprise AI Agent Intelligence Hub & Autonomous Test Quality Gate" \
      org.opencontainers.image.url="https://github.com/TeeVee98/Synapse-Hub" \
      org.opencontainers.image.source="https://github.com/TeeVee98/Synapse-Hub" \
      org.opencontainers.image.licenses="MIT" \
      org.opencontainers.image.authors="Thế Vị (@TeeVee98)"

# Core Environment Configuration
ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONUNBUFFERED=1 \
    LANG=C.UTF-8 \
    LC_ALL=C.UTF-8 \
    PIP_BREAK_SYSTEM_PACKAGES=1 \
    CHROME_BIN=/usr/bin/chromium \
    CHROMIUM_PATH=/usr/bin/chromium \
    PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD=1 \
    PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH=/usr/bin/chromium \
    PUPPETEER_SKIP_CHROMIUM_DOWNLOAD=true \
    PUPPETEER_EXECUTABLE_PATH=/usr/bin/chromium

# Install System Dependencies, Node.js 20, OpenJDK Headless, Git, and Headless Browser Libraries
RUN apt-get update && apt-get install -y --no-install-recommends \
    bash \
    ca-certificates \
    curl \
    git \
    gnupg \
    && mkdir -p /etc/apt/keyrings \
    && curl -fsSL https://deb.nodesource.com/gpgkey/nodesource-repo.gpg.key | gpg --dearmor -o /etc/apt/keyrings/nodesource.gpg \
    && echo "deb [signed-by=/etc/apt/keyrings/nodesource.gpg] https://deb.nodesource.com/node_20.x nodistro main" > /etc/apt/sources.list.d/nodesource.list \
    && apt-get update && apt-get install -y --no-install-recommends \
    nodejs \
    default-jre-headless \
    chromium \
    chromium-driver \
    libnss3 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libcups2 \
    libdrm2 \
    libxkbcommon0 \
    libxcomposite1 \
    libxdamage1 \
    libxfixes3 \
    libxrandr2 \
    libgbm1 \
    libpango-1.0-0 \
    libcairo2 \
    libasound2 \
    fonts-liberation \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Copy Synapse-Hub source into /opt/synapse-hub and install globally
WORKDIR /opt/synapse-hub
COPY . /opt/synapse-hub

# Create dedicated non-root service user and group (synapse: UID 10001, GID 10001)
RUN groupadd -g 10001 synapse \
    && useradd -u 10001 -g synapse -s /bin/bash -m synapse

# Install hermetic Python requirements and global npm package CLI
RUN pip install --no-cache-dir -r requirements.lock \
    && pip install --no-cache-dir -e . \
    && npm install -g . \
    && chmod +x bin/agent-qa.js

# Setup workspace directory and set ownership on /workspace and /opt/synapse-hub
RUN mkdir -p /workspace \
    && chown -R synapse:synapse /opt/synapse-hub /workspace \
    && chmod 777 /workspace

# Switch to non-root user
USER synapse
WORKDIR /workspace

# Default Entrypoint & Command
ENTRYPOINT ["synapse-hub"]
CMD ["--help"]
