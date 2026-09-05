# Use Debian 12 (bookworm) explicitly so package names stay stable.
FROM python:3.11-slim-bookworm

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    AISTUDIO_PORT=8080 \
    AISTUDIO_BROWSER=chromium \
    AISTUDIO_BROWSER_HEADLESS=1 \
    AISTUDIO_ACCOUNTS_DIR=/app/data/accounts

# Install system dependencies required for Camoufox and Playwright
RUN apt-get update && apt-get install -y --no-install-recommends \
    # Core libraries for Firefox/Camoufox
    libgtk-3-0 \
    libglib2.0-0 \
    libx11-6 \
    libx11-xcb1 \
    libxcomposite1 \
    libxdamage1 \
    libxrandr2 \
    libxext6 \
    libxfixes3 \
    libxi6 \
    libxtst6 \
    libasound2 \
    libpango-1.0-0 \
    libcairo2 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libgdk-pixbuf2.0-0 \
    libnspr4 \
    libnss3 \
    libdrm2 \
    libgbm1 \
    libxcb1 \
    libxkbcommon0 \
    libatspi2.0-0 \
    libwayland-client0 \
    libwayland-egl1 \
    libwayland-server0 \
    # Fonts
    fonts-liberation \
    fonts-noto-color-emoji \
    fonts-wqy-zenhei \
    # Utilities
    curl \
    procps \
    # Headed login display: Xvfb + VNC + noVNC (not a full desktop)
    xvfb \
    x11vnc \
    novnc \
    websockify \
    dbus-x11 \
    # Cleanup
    && rm -rf /var/lib/apt/lists/*

# Create app directory
WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY src/ src/
COPY main.py .
COPY config.yaml .
COPY docker/entrypoint.sh /usr/local/bin/aistudio-entrypoint
COPY docker/p1_headed_login.py /app/docker/p1_headed_login.py

# Create necessary directories
RUN mkdir -p /app/data /root/.cloakbrowser /tmp \
    && sed -i 's/\r$//' /usr/local/bin/aistudio-entrypoint /app/docker/p1_headed_login.py \
    && chmod +x /app/main.py /usr/local/bin/aistudio-entrypoint /app/docker/p1_headed_login.py

# Expose ports
# 8080: API server
# 6080: noVNC (publish to host loopback only; do not map 5900 or 9222)
EXPOSE 8080 6080

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
    CMD curl --fail --silent --show-error http://localhost:8080/health || exit 1

# Default command
ENTRYPOINT ["aistudio-entrypoint"]
CMD ["python3", "main.py", "server", "--port", "8080", "--browser-port", "9222"]
