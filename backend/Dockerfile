# Arguments de build
ARG PYTHON_VERSION=3.10

FROM python:${PYTHON_VERSION}-slim

LABEL maintainer="Evolutek Team"
LABEL description="FastAPI Backend for drone mission management"
LABEL python.version="${PYTHON_VERSION}"

WORKDIR /app

# Installation dépendances système
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copie requirements
COPY requirements.txt .

# Installation packages Python
RUN pip install --no-cache-dir -r requirements.txt

# Copie code application
COPY app/ app/

# Création répertoires données
RUN mkdir -p /app/data

EXPOSE 8000

# Healthcheck
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:8000/health')"

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
