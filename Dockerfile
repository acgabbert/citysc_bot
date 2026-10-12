FROM python:3.13-slim-bookworm

WORKDIR /app

# Create a non-root user with UID 1000
RUN useradd -u 1000 -m botuser

# Install Python dependencies system-wide, then the system libraries Playwright's
# Chromium needs (install-deps uses apt, so it runs as root)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt && \
    playwright install-deps chromium && \
    apt-get update && apt-get install -y --no-install-recommends fonts-noto-color-emoji && \
    rm -rf /var/lib/apt/lists/*

# Create required directories with proper permissions
RUN mkdir -p assets models log png data && \
    chown -R 1000:1000 /app && \
    chmod 755 /app/assets /app/models /app/log /app/png /app/data

# Switch to UID 1000 for subsequent commands
USER 1000

# Download Playwright's Chromium into botuser's cache
RUN playwright install chromium

# Copy the source code
COPY --chown=1000:1000 *.py ./
COPY --chown=1000:1000 models/*.py ./models/
RUN rm -f config*.py
COPY --chown=1000:1000 *.sh ./

# Add the app directory to PYTHONPATH
ENV PYTHONPATH=/app

RUN chmod +x entrypoint.sh

# async_controller.py touches this file every minute while its event loop runs
HEALTHCHECK --interval=1m --timeout=10s --start-period=2m --retries=3 \
    CMD python -c "import os, sys, time; sys.exit(time.time() - os.path.getmtime('/tmp/citysc_bot.heartbeat') > 300)"

ENTRYPOINT ["/bin/bash", "./entrypoint.sh"]
CMD ["python", "async_controller.py"]
