#!/bin/bash

# Check for required config
if [ ! -f "/app/config.py" ]; then
    echo "Error: config.py not found at /app/config.py"
    exit 1
fi

# Check for required directories in /app
for dir in assets markdown log png; do
    if [ ! -d "/app/$dir" ]; then
        echo "Creating /app/$dir directory"
        mkdir -p "/app/$dir"
    fi
    # Ensure proper ownership and permissions using UID
    chown -R 1000:1000 "/app/$dir"
    chmod 755 "/app/$dir"
done

echo "Starting main application..."
exec "$@"