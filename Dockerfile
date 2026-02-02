# Dockerfile for Pyppeteer in a Streamlit app
FROM python:3.10-slim

# 1. Install system dependencies AND Google Chrome (Stable)
RUN apt-get update && apt-get install -y \
    gdal-bin libgdal-dev \
    build-essential \
    wget \
    fonts-liberation libasound2 libatk-bridge2.0-0 \
    libnspr4 libnss3 libx11-xcb1 libxcomposite1 libxrandr2 \
    xdg-utils \
    # Install Google Chrome (Stable) - NOUVELLE MÉTHODE
    && wget -q -O - https://dl.google.com/linux/linux_signing_key.pub > /usr/share/keyrings/google-chrome.asc \
    && echo "deb [arch=amd64 signed-by=/usr/share/keyrings/google-chrome.asc] http://dl.google.com/linux/chrome/deb/ stable main" > /etc/apt/sources.list.d/google-chrome.list \
    && apt-get update && apt-get install -y google-chrome-stable \
    && rm -rf /var/lib/apt/lists/*

# 2. Set Pyppeteer environment variable to skip automatic download
ENV PUPPETEER_SKIP_CHROMIUM_DOWNLOAD=true
ENV PYPPETEER_CHROMIUM_REVISION=""

# 3. GDAL configuration (keep your existing settings)
ENV CPLUS_INCLUDE_PATH=/usr/include/gdal
ENV C_INCLUDE_PATH=/usr/include/gdal

WORKDIR /app

COPY requirements.txt .
RUN pip install --upgrade pip \
    && pip install --no-cache-dir numpy \
    && pip install --no-cache-dir -r requirements.txt \
    && pip install --no-cache-dir gdal==3.10.*

COPY . .

RUN mkdir -p /root/.streamlit && \
    echo '[server]\n\
headless = true\n\
address = "0.0.0.0"\n\
port = 10000\n\
enableCORS = false\n\
enableXsrfProtection = false\n\
\n\
[browser]\n\
gatherUsageStats = false' > /root/.streamlit/config.toml

EXPOSE 10000

# CRITICAL for Render: Use port 10000 and ensure the server listens on 0.0.0.0
CMD ["streamlit", "run", "app.py", "--server.port=10000", "--server.address=0.0.0.0"]