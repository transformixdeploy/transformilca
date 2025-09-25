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

# Install Google Chrome stable
RUN wget -qO- https://dl.google.com/linux/linux_signing_key.pub | gpg --dearmor -o /usr/share/keyrings/google-linux-signing-keyring.gpg \
 && echo "deb [arch=amd64 signed-by=/usr/share/keyrings/google-linux-signing-keyring.gpg] http://dl.google.com/linux/chrome/deb/ stable main" > /etc/apt/sources.list.d/google-chrome.list \
 && apt-get update \
 && apt-get install -y --no-install-recommends google-chrome-stable \
 && rm -rf /var/lib/apt/lists/*

# Install matching Chromedriver
RUN CHROME_VERSION=$(google-chrome --version | awk '{print $3}') \
 && MAJOR=$(echo $CHROME_VERSION | cut -d. -f1) \
 && LATEST=$(wget -qO- https://chromedriver.storage.googleapis.com/LATEST_RELEASE_$MAJOR) \
 && wget -O /tmp/chromedriver.zip https://chromedriver.storage.googleapis.com/$LATEST/chromedriver_linux64.zip \
 && unzip /tmp/chromedriver.zip -d /usr/local/bin/ \
 && rm /tmp/chromedriver.zip \
 && chmod +x /usr/local/bin/chromedriver

WORKDIR /app

# Python deps
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt \
 && pip install --no-cache-dir waitress

# App code
COPY . .

# Env expected to be provided by Render
ENV PYTHONUNBUFFERED=1

# Health: avoid TF noisy logs (optional)
ENV TF_CPP_MIN_LOG_LEVEL=2

# Start the web service (Render injects $PORT)
CMD ["waitress-serve", "--listen=0.0.0.0:${PORT}", "flask_api:app"]


