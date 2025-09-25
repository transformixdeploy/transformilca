FROM python:3.12-slim

# Prevent interactive prompts
ENV DEBIAN_FRONTEND=noninteractive

# System dependencies
RUN apt-get update \
 && apt-get install -y --no-install-recommends \
    wget \
    gnupg \
    unzip \
    ca-certificates \
    fonts-liberation \
    libglib2.0-0 \
    libnss3 \
    libfontconfig1 \
    libxi6 \
    libxcursor1 \
    libxcomposite1 \
    libasound2 \
    libxdamage1 \
    libxrandr2 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libxkbcommon0 \
    libc6 \
    libdrm2 \
    libgbm1 \
    libgtk-3-0 \
    libpango-1.0-0 \
    libpangocairo-1.0-0 \
 && rm -rf /var/lib/apt/lists/*

# Install Chromium and matching driver from Debian repos
RUN apt-get update \
 && apt-get install -y --no-install-recommends chromium chromium-driver \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Python deps
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt \
 && pip install --no-cache-dir waitress

# App code
COPY . .

# Env expected to be provided by Render
ENV PYTHONUNBUFFERED=1
ENV CHROME_BIN=/usr/bin/chromium

# Health: avoid TF noisy logs (optional)
ENV TF_CPP_MIN_LOG_LEVEL=2

# Start the web service (Render injects $PORT)
CMD ["waitress-serve", "--listen=0.0.0.0:${PORT}", "flask_api:app"]


