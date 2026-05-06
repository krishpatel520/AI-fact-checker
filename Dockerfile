# ─────────────────────────────────────────────────────────────────────────────
# Stage 1: Builder — install Python deps into a venv
# ─────────────────────────────────────────────────────────────────────────────
FROM python:3.11-slim AS builder

WORKDIR /build

# System deps required by lxml, PyMuPDF, psycopg2, newspaper3k
RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential \
        libpq-dev \
        libxml2-dev \
        libxslt1-dev \
        libffi-dev \
        gcc \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --upgrade pip && \
    pip install --no-cache-dir --prefix=/install -r requirements.txt

# Download spaCy model into the install prefix
RUN PYTHONPATH=/install/lib/python3.11/site-packages \
    python -m spacy download en_core_web_sm --target /install/lib/python3.11/site-packages


# ─────────────────────────────────────────────────────────────────────────────
# Stage 2: Runtime — minimal image
# ─────────────────────────────────────────────────────────────────────────────
FROM python:3.11-slim AS runtime

WORKDIR /app

# Runtime system libs only
RUN apt-get update && apt-get install -y --no-install-recommends \
        libpq5 \
        libxml2 \
        libxslt1.1 \
    && rm -rf /var/lib/apt/lists/*

# Copy installed packages from builder
COPY --from=builder /install /usr/local

# Copy application source
COPY backend/ ./backend/
COPY .env.example .env.example

# Non-root user for security
RUN useradd -m -u 1000 veritas && chown -R veritas:veritas /app
USER veritas

# Entrypoint script selects API or Worker mode via MODE env variable
COPY --chown=veritas:veritas docker-entrypoint.sh /app/docker-entrypoint.sh
RUN chmod +x /app/docker-entrypoint.sh

EXPOSE 8000

ENTRYPOINT ["/app/docker-entrypoint.sh"]
