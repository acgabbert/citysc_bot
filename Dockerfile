FROM python:3.11-slim-bookworm

# Install system dependencies and Chrome
RUN apt-get update && apt-get install -y \
    wget \
    unzip \
    gnupg2 \
    software-properties-common \
    ca-certificates \
    && wget -q -O - https://dl.google.com/linux/linux_signing_key.pub | gpg --dearmor -o /usr/share/keyrings/google-chrome.gpg \
    && echo "deb [arch=amd64 signed-by=/usr/share/keyrings/google-chrome.gpg] http://dl.google.com/linux/chrome/deb/ stable main" >> /etc/apt/sources.list.d/google-chrome.list \
    && apt-get update \
    && apt-get install -y chromium=132.0.6834.159-1~deb12u1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /citysc_bot

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN wget -q "https://storage.googleapis.com/chrome-for-testing-public/132.0.6834.159/linux64/chromedriver-linux64.zip" \
    && unzip chromedriver-linux64.zip -d /usr/local/bin/ \
    && rm chromedriver-linux64.zip \
    && chmod +x /usr/local/bin/chromedriver-linux64/chromedriver \
    && mv /usr/local/bin/chromedriver-linux64/chromedriver /usr/local/bin/chromedriver

# Create a non-root user
RUN useradd -m botuser && chown -R botuser:botuser /citysc_bot
USER botuser

# Set Chrome options for running in container
ENV CHROME_OPTIONS="--headless --no-sandbox --disable-dev-shm-usage"

# Command to run the bot
CMD ["python", "controller.py"]