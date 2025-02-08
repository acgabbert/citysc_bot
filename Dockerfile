FROM python:3.11-slim-bookworm

# Install system dependencies and Chromium
RUN apt-get update && apt-get install -y \
    wget \
    unzip \
    chromium \
    chromium-driver \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /citysc_bot

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN mkdir -p /citysc_bot/assets /citysc_bot/markdown /citysc_bot/log /citysc_bot/png

# Create a non-root user
RUN useradd -m botuser && chown -R botuser:botuser /citysc_bot
USER botuser

# Set Chrome options for running in container
ENV CHROME_OPTIONS="--headless --no-sandbox --disable-dev-shm-usage"

# Command to run the bot
CMD ["python", "controller.py"]