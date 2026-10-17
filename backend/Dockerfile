FROM python:3.12-slim AS base

# Create nonroot user
RUN groupadd -r orbitlab && useradd -r -g orbitlab orbitlab

# Install dependencies
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source
COPY backend/app ./app
COPY backend/pyproject.toml .

WORKDIR /app

# Create SQLite directory writable by nonroot
RUN mkdir -p /data && chown orbitlab:orbitlab /data

USER orbitlab

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" 2>/dev/null || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]