#!/bin/bash

# debug output
echo "Current directory: $(pwd)"
echo "Listing directory contents:"
ls -la

# Initialize directory structure if mounting to empty directory
if [ -n "$INIT_DIR" ]; then
    echo "Checking INIT_DIR: $INIT_DIR"
    for dir in assets markdown log png; do
        if [ ! -d "$INIT_DIR/$dir" ]; then
            echo "Creating $INIT_DIR/$dir"
            mkdir -p "$INIT_DIR/$dir"
        fi
    done
    
    if [ ! -f "$INIT_DIR/config.py" ]; then
        echo "Copying config-example.py to $INIT_DIR/config.py"
        cp -n /app/config-example.py "$INIT_DIR/config.py"
    fi
fi

echo "Starting main application..."
exec "$@"