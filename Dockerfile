ARG BUILD_FROM
FROM ${BUILD_FROM}

# Set working directory
WORKDIR /app

# Install system dependencies (python3 and venv; PEP 668 blocks system pip install)
RUN apk add --no-cache \
    python3 \
    py3-pip \
    python3-dev \
    sqlite \
    wget

# Use a virtual environment so pip install is allowed (PEP 668)
RUN python3 -m venv /app/venv
ENV PATH="/app/venv/bin:$PATH"

# Copy requirements and install Python dependencies into venv
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code and migration script
COPY app/ ./app/
COPY run.sh .
COPY migrate_database.py .

# Ensure run.sh has Unix line endings (avoids silent fail when add-on starts)
RUN sed -i 's/\r$//' run.sh

# Create data directory for SQLite database
RUN mkdir -p /data

# Set permissions
RUN chmod +x run.sh

# Expose port
EXPOSE 5050

# Health check (HTTP 200 on /health); long start-period for first-time DB init + migrate
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=5 \
    CMD wget -q -O /dev/null http://127.0.0.1:5050/health || exit 1

# Run our app as PID 1; base image uses s6-overlay and suexec, which fails when not PID 1
ENTRYPOINT []
CMD ["./run.sh"]
