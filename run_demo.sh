#!/usr/bin/env bash
cd "$(dirname "$0")"

if [ -f "venv/bin/activate" ]; then
    source venv/bin/activate
else
    echo "Virtual environment not found at venv/bin/activate"
    echo "Continuing with system Python..."
fi

python3 run_demo.py