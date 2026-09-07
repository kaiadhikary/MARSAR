# Offline Air-Gapped Container Environment for Linux evaluation
FROM python:3.11-slim

# Set environment variables for non-interactive offline execution
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DEBIAN_FRONTEND=noninteractive \
    MARSAR_AIRGAP=1

WORKDIR /app

# Install base system utilities required for local compiling
# Dependencies are installed at image-build time. Runtime needs no network access.
# For a fully disconnected build, provide a wheelhouse and replace this command
# with: pip install --no-index --find-links=/wheels -r requirements.txt
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend application source and forensic data
COPY . .

# Initialize offline forensic database and generate baseline synthetic dataset
RUN python -c "from app.db.sqlite_client import init_db; init_db()" && \
    python generate_synthetic_dataset.py

EXPOSE 8000

# Default entrypoint launches the FastAPI forensic server
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
