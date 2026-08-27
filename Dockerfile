# Stage 1: Build React Frontend static bundle
FROM node:18-alpine AS frontend-builder

WORKDIR /frontend
COPY frontend/package*.json ./
RUN npm install
COPY frontend/ ./
RUN npm run build

# Stage 2: Production Python FastAPI Application
FROM python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PORT=8000

# Set work directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend code
COPY app /app/app

# Copy built frontend SPA assets from stage 1
COPY --from=frontend-builder /frontend/dist /app/frontend/dist

# Create folders for SQLite database, datasets, and ML model artifacts
RUN mkdir -p /app/data /app/data/raw /app/data/cleaned /app/models

# Expose port
EXPOSE 8000

# Command to run application
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port $PORT"]

