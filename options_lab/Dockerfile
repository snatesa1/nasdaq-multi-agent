# ==============================================================================
# Dedicated Dockerfile for OptionsLab Backend
# ==============================================================================
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl gcc python3-dev && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy OptionsLab codebase
COPY api/ ./api/
COPY engine/ ./engine/

# Create persistent data mount point
RUN mkdir -p /app/data

ENV HOST=0.0.0.0
ENV PORT=8000
ENV DB_DATA_DIR=/app/data

EXPOSE 8000

CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]
