FROM python:3.11-slim

# Install git and build dependencies
RUN apt-get update && \
    apt-get install -y \
    git \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Create and set non-root user
RUN useradd -m -s /bin/bash appuser

# Create application directory
WORKDIR /app

# Copy requirements first to leverage Docker cache
COPY requirements.txt .
RUN pip install -r requirements.txt

# Create directories with appropriate permissions
RUN mkdir -p /data/upload /data/aim && \
    chown -R appuser:appuser /data

# Copy application code
COPY . .
RUN chown -R appuser:appuser /app && \
    chmod -R 755 /app

# Switch to non-root user
USER appuser

# Set environment variables
ENV UPLOAD_DIR=/data/upload
ENV AIM_REPO=/data/.aim
ENV AIM_REMOTE_PORT=8000

# Expose the port
EXPOSE 8000

# Mount the upload directory from the host
VOLUME /data/upload
VOLUME /data/.aim
CMD ["python", "main.py"]

# Example Docker run command
# docker run -d -p 8000:8000 -v $(pwd)/upload:/data/upload -v $(pwd)/.aim:/data/.aim aim_remote
