#!/usr/bin/env bash
# Launch the full Lumina Desk system.
#   - MQTT broker (mosquitto) runs as a systemd service (always on).
#   - display service owns the ePaper panel and subscribes to the bus.
#   - voice app runs in the foreground and publishes to the bus.
cd "$(dirname "$0")"

# Start the display service in the background (-u so its log isn't buffered).
./venv/bin/python -u display_service.py > /tmp/lumina_display.log 2>&1 &
DISP_PID=$!
trap "kill $DISP_PID 2>/dev/null" EXIT
sleep 1   # let it connect to the broker before the voice app publishes

exec ./venv/bin/python wake_listen.py
