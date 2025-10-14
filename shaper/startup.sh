#!/bin/bash
set -e

echo "Setting up traffic shaper..."

# Enable IP forwarding
sysctl -w net.ipv4.ip_forward=1

# Wait a moment for interfaces to be ready
sleep 2

echo "Starting Flask controller..."
exec python3 /app/shaping-controller.py