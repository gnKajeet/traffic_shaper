#!/bin/bash

# Quick test of a single policy
POLICY=${1:-"mobile_4g"}

echo "Testing policy: $POLICY"

# Apply policy
curl -s -X POST http://localhost:5000/policy/apply \
  -H "Content-Type: application/json" \
  -d "{\"policy\": \"$POLICY\"}" | jq

# Wait a moment
sleep 2

# Run iperf
echo -e "\nRunning iperf3 test..."
docker exec iperf_client iperf3 -c 172.21.0.3 -t 10

# Clear policy
curl -s -X POST http://localhost:5000/policy/clear | jq