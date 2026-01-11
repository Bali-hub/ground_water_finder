# Dockerfile - OPTIMISÉ POUR RENDER
FROM python:3.10-slim

# 1. DÉPENDANCES SYSTÈME
RUN apt-get update && apt-get install -y \
    gdal-bin libgdal-dev \
    wget gnupg libnss3 libatk1.0-0 libatk-bridge2.0-0 \
    libxcomposite1 libxrandr2 libgbm1 libasound2 \
    && rm -rf /var/lib/apt/lists/*

# 2. WORKDIR
WORKDIR /app

# 3. COPY ET INSTALL
COPY requirements.txt .
RUN pip install --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt && \
    playwright install chromium

# 4. COPY APP
COPY . .

# 5. PORT (utiliser $PORT de Render)
EXPOSE 8501

# 6. COMMANDE (utiliser $PORT variable)
CMD ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]