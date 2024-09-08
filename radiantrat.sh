#!/bin/bash
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cat "$SCRIPT_DIR/ratbanner.txt"
mkdir -p $SCRIPT_DIR/logs
cd "$SCRIPT_DIR/logs"

setsid python3 "$SCRIPT_DIR/hub_config/rathub.py" > /dev/null 2>&1 &
PYTHON_PID=$!

echo "See http://localhost:4000 for RadiantRat UI, or http://localhost:2501 for Kismet."
echo "If using VM, make sure you replace 'localhost' with the VM's IP."
echo ""
while true; do
    read -p "Press 'q' to quit: " setting
    if [[ $setting == 'q' ]]; then
        if ps -p $PYTHON_PID > /dev/null; then
            kill -TERM -$PYTHON_PID
        fi
        break
    fi
done
