# --- Stage 1: Builder (The Construction Site) ---
FROM python:3.11-slim as builder

WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Install compilers (needed for some python packages)
RUN apt-get update && apt-get install -y \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Create a virtual environment
RUN python -m venv /opt/venv
# Enable the venv for the following commands
ENV PATH="/opt/venv/bin:$PATH"

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# --- Stage 2: Final (The Production Image) ---
FROM python:3.11-slim

WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Copy the virtual environment from the builder stage
COPY --from=builder /opt/venv /opt/venv

# Enable the venv in the final image
ENV PATH="/opt/venv/bin:$PATH"

# Copy your application code
COPY . .

# (Optional) Use a non-root user for security
RUN useradd -m appuser
USER appuser

CMD ["bash"] 
# Note: Your docker-compose command overrides this CMD, so "bash" is just a placeholder