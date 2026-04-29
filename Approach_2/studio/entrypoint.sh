#!/bin/bash
set -e

# Set window variables
export DISPLAY=:0
export RESOLUTION=1920x1080x24

echo "Starting Xvfb..."
Xvfb $DISPLAY -screen 0 $RESOLUTION &
sleep 2

echo "Starting Openbox window manager..."
openbox-session &
sleep 1

echo "Starting x11vnc..."
x11vnc -display $DISPLAY -forever -nopw -bg -xkb -quiet

echo "Starting websockify via noVNC..."
websockify --web /usr/share/novnc 6080 localhost:5900 &

echo "Launching Slideflow Studio..."
# Run slideflow studio script forever
python3 /app/run_studio.py
