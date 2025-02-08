#!/bin/bash

# Initialize directory structure if mounting to empty directory
if [ -n "$INIT_DIR" ] && [ ! -f "$INIT_DIR/config.py" ]; then
    echo "Initializing directory structure in $INIT_DIR"
    mkdir -p "$INIT_DIR/assets"
    mkdir -p "$INIT_DIR/markdown"
    mkdir -p "$INIT_DIR/log"
    mkdir -p "$INIT_DIR/png"
    cp -n /citysc_bot/config-example.py "$INIT_DIR/config.py"
fi

exec "$@"