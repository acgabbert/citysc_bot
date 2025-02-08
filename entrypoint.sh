#!/bin/bash

# Add debug output
echo "Current directory: $(pwd)"
echo "Listing directory contents:"
ls -la
echo "Current user: $(id)"

# Check for required config
if [ ! -f "/app/config.py" ]; then
    echo "Error: config.py not found at /app/config.py"
    exit 1
fi

# Check for required directories in /app
for dir in assets markdown log png; do
    if [ ! -d "/app/$dir" ]; then
        echo "Warning: /app/$dir directory not found"
    fi
done

echo "Starting main application..."
exec "$@"