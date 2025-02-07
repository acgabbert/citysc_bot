FROM python:3.11-slim-buster as base

WORKDIR /citysc_bot

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Create a non-root user
RUN useradd -m botuser && chown -R botuser:botuser /app
USER botuser

# Command to run the bot
CMD ["python", "controller.py"]