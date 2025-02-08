#!/bin/bash

# Add debug output
echo "Current directory: $(pwd)"
echo "Listing directory contents:"
ls -la

# Check for config.py
if [ ! -f "/app/config.py" ]; then
    echo "Error: config.py not found. Please create config.py in ${INIT_DIR}"
    echo "You can use config-example.py as a template"
    exit 1
fi

# Initialize directory structure if mounting to empty directory
if [ -n "$INIT_DIR" ]; then
    echo "Checking INIT_DIR: $INIT_DIR"
    for dir in assets markdown log png; do
        if [ ! -d "$INIT_DIR/$dir" ]; then
            echo "Creating $INIT_DIR/$dir"
            mkdir -p "$INIT_DIR/$dir"
        fi
    done
fi

echo "Starting main application..."
exec "$@"