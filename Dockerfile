# syntax=docker/dockerfile:1

# =====================================================
# STAGE 1 — BUILDER
# =====================================================
FROM python:3.10-slim-bookworm AS builder

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libgdal-dev \
    gdal-bin \
    curl \
    libgl1 \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender1 \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .

RUN pip install --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

# =====================================================
# STAGE 2 — RUNTIME FINAL
# =====================================================
FROM python:3.10-slim-bookworm

WORKDIR /app

# -----------------------------------------------------
# Dépendances runtime + Chrome
# -----------------------------------------------------
RUN apt-get update && apt-get install -y --no-install-recommends \
    gdal-bin \
    libgdal-dev \
    libasound2 libatk-bridge2.0-0 libatk1.0-0 libcairo2 \
    libcups2 libdbus-1-3 libexpat1 libfontconfig1 libgbm1 \
    libgl1 \
    libegl1 \
    libglib2.0-0 libgtk-3-0 libnspr4 libnss3 \
    libpango-1.0-0 libpangocairo-1.0-0 \
    libx11-6 libx11-xcb1 libxcb1 \
    libxcomposite1 libxcursor1 libxdamage1 libxext6 libxfixes3 \
    libxi6 libxrandr2 libxrender1 libxss1 libxtst6 \
    libsm6 libice6 \
    fonts-liberation wget gnupg ca-certificates \
    && mkdir -p /etc/apt/keyrings \
    && wget -qO /etc/apt/keyrings/google.asc https://dl.google.com/linux/linux_signing_key.pub \
    && gpg --dearmor -o /etc/apt/keyrings/google.gpg /etc/apt/keyrings/google.asc \
    && echo "deb [arch=amd64 signed-by=/etc/apt/keyrings/google.gpg] http://dl.google.com/linux/chrome/deb/ stable main" > /etc/apt/sources.list.d/google-chrome.list \
    && apt-get update \
    && apt-get install -y google-chrome-stable \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/* \
    && rm -rf /tmp/*

# -----------------------------------------------------
# Installer le client Docker (pour l'orchestrateur)
# -----------------------------------------------------
RUN apt-get update && apt-get install -y --no-install-recommends docker.io \
    && rm -rf /var/lib/apt/lists/*

# -----------------------------------------------------
# Copier Python depuis builder
# -----------------------------------------------------
COPY --from=builder /usr/local/lib/python3.10/site-packages /usr/local/lib/python3.10/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# -----------------------------------------------------
# Variables d'environnement
# -----------------------------------------------------
ENV PUPPETEER_SKIP_CHROMIUM_DOWNLOAD=1 \
    CHROME_PATH=/usr/bin/google-chrome \
    PYTHONUNBUFFERED=1 \
    STREAMLIT_SERVER_PORT=10000 \
    STREAMLIT_SERVER_ADDRESS=0.0.0.0 \
    CPLUS_INCLUDE_PATH=/usr/include/gdal \
    C_INCLUDE_PATH=/usr/include/gdal \
    MPLBACKEND=Agg \
    QT_QPA_PLATFORM=offscreen \
    XDG_RUNTIME_DIR=/tmp/runtime-root

# -----------------------------------------------------
# Créer les répertoires nécessaires (root)
# -----------------------------------------------------
RUN mkdir -p /tmp/.matplotlib /tmp/runtime-root \
    && chmod 777 /tmp/.matplotlib /tmp/runtime-root

# -----------------------------------------------------
# Copier le code
# -----------------------------------------------------
COPY . .

# -----------------------------------------------------
# Workspace monté (volumes)
# -----------------------------------------------------
RUN mkdir -p /workspace && chmod 777 /workspace

# -----------------------------------------------------
# Créer l'utilisateur non-root
# -----------------------------------------------------
RUN groupadd -r appuser && useradd -r -m -g appuser appuser \
    && mkdir -p /home/appuser/.streamlit /home/appuser/.config/matplotlib \
    && printf "[server]\nheadless=true\naddress=\"0.0.0.0\"\nport=10000\nenableCORS=false\nenableXsrfProtection=false\n[browser]\ngatherUsageStats=false\n" > /home/appuser/.streamlit/config.toml \
    && printf "backend: Agg\n" > /home/appuser/.config/matplotlib/matplotlibrc \
    && chown -R appuser:appuser /app /home/appuser

# -----------------------------------------------------
# Ajouter appuser au groupe docker (après création de l'utilisateur)
# -----------------------------------------------------

# Le groupe docker existe déjà après l'installation de docker.io
RUN usermod -aG docker appuser

# -----------------------------------------------------
# Créer le dossier temporaire pour les cartes
# -----------------------------------------------------
RUN mkdir -p /home/appuser/temp_cartes && \
    chown -R appuser:appuser /home/appuser/temp_cartes

# -----------------------------------------------------
# Passer à l'utilisateur non-root
# -----------------------------------------------------
# USER appuser

WORKDIR /workspace

EXPOSE 10000

CMD ["streamlit", "run", "/app/app.py", "--server.port=10000", "--server.address=0.0.0.0", "--server.headless=true", "--browser.gatherUsageStats=false"]