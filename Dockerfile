FROM python:3.13-slim-bookworm

# Install system dependencies and Chromium
RUN apt-get update && apt-get install -y \
    wget \
    unzip \
    chromium \
    chromium-driver \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Create a non-root user
RUN useradd -m botuser && chown -R botuser:botuser /app

# Create required directories with proper permissions
RUN mkdir assets markdown log png && \
    chown -R 1000:1000 /app

# Switch to botuser before installing Python packages
USER botuser

# Copy requirements first to leverage Docker cache
COPY --chown=botuser:botuser requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install Playwright and browsers
RUN pip install --user playwright
ENV PATH="/home/botuser/.local/bin:${PATH}"
RUN playwright install --with-deps chromium

# Copy the source code
COPY --chown=botuser:botuser *.py ./
RUN rm -f config*.py
COPY --chown=botuser:botuser *.sh ./

# Add the app directory to PYTHONPATH
ENV PYTHONPATH=/app

# Set Chrome options for running in container
ENV CHROME_OPTIONS="--headless --no-sandbox --disable-dev-shm-usage"

RUN chmod +x entrypoint.sh

ENTRYPOINT ["/bin/bash", "./entrypoint.sh"]
CMD ["python", "async_controller.py"]