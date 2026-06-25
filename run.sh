#!/bin/bash
echo "Installing dependencies..."
pip install flask flask-socketio eventlet --break-system-packages -q
echo ""
echo "Starting Living Reading server..."
echo ""
python app.py
