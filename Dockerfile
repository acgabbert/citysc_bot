FROM python:3.11-slim-bookworm

# Install system dependencies and Chromium
RUN apt-get update && apt-get install -y \
    wget \
    unzip \
    chromium \
    chromium-driver \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy requirements first to leverage Docker cache
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the source code
COPY *.py ./
RUN rm -f config*.py
COPY *.sh ./

# Create required directories with proper permissions
RUN mkdir assets markdown log png && \
    chown -R 1000:1000 /app

# Create a non-root user
RUN useradd -m botuser && chown -R botuser:botuser /app
USER botuser

# Add the app directory to PYTHONPATH
ENV PYTHONPATH=/app

# Set Chrome options for running in container
ENV CHROME_OPTIONS="--headless --no-sandbox --disable-dev-shm-usage"

RUN chmod +x entrypoint.sh

ENTRYPOINT ["/bin/bash", "./entrypoint.sh"]
CMD ["python", "controller.py"]