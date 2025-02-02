FROM python:3.11-slim

# Install git and build dependencies
RUN apt-get update && \
    apt-get install -y \
    git \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Create application directory
WORKDIR /app

# Copy requirements first to leverage Docker cache
COPY requirements.txt .
RUN pip install -r requirements.txt

# Copy application code
COPY . .

# Set read-only permissions for application code and Python
RUN chmod -R 555 /app && \
    chmod -R 555 /usr/local/lib/python* && \
    chmod -R 555 /usr/local/bin

# Set environment variables
ENV UPLOAD_DIR=/data/upload
ENV AIM_REPO=/data/.aim
ENV SESSKEY_FNAME=/data/sesskey/.sesskey
ENV AIM_REMOTE_PORT=8000

# Expose the port
EXPOSE 8000

# Mount the upload directory from the host
VOLUME /data/upload
VOLUME /data/.aim
VOLUME /data/sesskey
CMD ["python", "main.py"]

# Example Docker run command
# docker run -d -p 8000:8000 -v $(pwd)/upload:/data/upload -v $(pwd)/.aim:/data/.aim -v $(pwd)/sesskey:/data/sesskey aim_remote
