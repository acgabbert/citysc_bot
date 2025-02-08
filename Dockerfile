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
COPY entrypoint.sh /entrypoint.sh

# Create required directories
RUN mkdir -p assets markdown log png

# Create a non-root user
RUN useradd -m botuser && chown -R botuser:botuser /app
USER botuser

# Set Chrome options for running in container
ENV CHROME_OPTIONS="--headless --no-sandbox --disable-dev-shm-usage"

RUN chmod +x /entrypoint.sh

ENTRYPOINT ["/entrypoint.sh"]
CMD ["python", "controller.py"]