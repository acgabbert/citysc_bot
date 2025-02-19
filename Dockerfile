FROM python:3.13-slim-bookworm

# Install system dependencies as root
RUN apt-get update && apt-get install -y \
    wget \
    unzip \
    chromium \
    chromium-driver \
    xvfb \
    libgbm1 \
    libnss3 \
    libxss1 \
    libasound2 \
    libatk-bridge2.0-0 \
    libgtk-3-0 \
    fonts-noto-color-emoji \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Create a non-root user with UID 1000
RUN useradd -u 1000 -m botuser 

# Create required directories with proper permissions
RUN mkdir -p assets markdown log png && \
    chown -R 1000:1000 /app && \
    chmod 755 /app/assets && \
    chmod 755 /app/markdown && \
    chmod 755 /app/log && \
    chmod 755 /app/png

# Switch to UID 1000 for subsequent commands
USER 1000

# Copy requirements first to leverage Docker cache
COPY --chown=1000:1000 requirements.txt .
RUN pip install --user --no-cache-dir -r requirements.txt

# Install Playwright and browser as botuser
RUN pip install --user playwright
ENV PATH="/home/botuser/.local/bin:${PATH}"
RUN playwright install chromium

# Copy the source code
COPY --chown=1000:1000 *.py ./
RUN rm -f config*.py
COPY --chown=1000:1000 *.sh ./
COPY --chown=1000:1000 *.json ./

# Add the app directory to PYTHONPATH
ENV PYTHONPATH=/app

# Set Chrome options for running in container
ENV CHROME_OPTIONS="--headless --no-sandbox --disable-dev-shm-usage"

RUN chmod +x entrypoint.sh

ENTRYPOINT ["/bin/bash", "./entrypoint.sh"]
CMD ["python", "async_controller.py"]
