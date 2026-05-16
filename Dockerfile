FROM python:3.11-slim

WORKDIR /app

# Install system dependencies for openpyxl and numpy
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libc6-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better layer caching
COPY intraday-scanner/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY intraday-scanner/ ./intraday-scanner/
COPY .streamlit/ ./.streamlit/

# Expose Streamlit port
EXPOSE 8500

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8500/_stcore/health')" || exit 1

# Run the application
CMD ["streamlit", "run", "intraday-scanner/app.py", "--server.port=8500", "--server.address=0.0.0.0"]
