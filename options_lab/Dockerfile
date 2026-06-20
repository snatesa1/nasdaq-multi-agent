# ==========================================
# Stage 1: Build the frontend Next.js app
# ==========================================
FROM node:20-alpine AS frontend-builder
WORKDIR /app/frontend

COPY frontend/package*.json ./
RUN npm install --legacy-peer-deps

COPY frontend/ ./
# Build and export to HTML
RUN npm run build

# ==========================================
# Stage 2: Serve API and Static Files
# ==========================================
FROM python:3.11-slim AS backend-server
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl && rm -rf /var/lib/apt/lists/*

# Copy backend files and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend codebase
COPY api/ ./api/
COPY engine/ ./engine/

# Copy compiled static frontend output
COPY --from=frontend-builder /app/frontend/out ./frontend/out

EXPOSE 8080

CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8080"]
