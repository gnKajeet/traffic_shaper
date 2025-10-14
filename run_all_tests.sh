#!/bin/bash

# Script to test all traffic shaping policies and generate CSV report
# Run this on the droplet or through SSH tunnel

set -e

# Configuration
API_URL="${API_URL:-http://localhost:5000}"
OUTPUT_FILE="${OUTPUT_FILE:-policy_test_results.csv}"
TEST_DURATION="${TEST_DURATION:-10}"

echo "Traffic Shaping Policy Test Suite"
echo "=================================="
echo "API URL: $API_URL"
echo "Test Duration: ${TEST_DURATION}s per policy"
echo "Output File: $OUTPUT_FILE"
echo ""

# Create CSV header
echo "Policy,Bitrate_Sender_Mbps,Bitrate_Receiver_Mbps,Transfer_Sender_MB,Transfer_Receiver_MB,Retransmissions,Avg_RTT_ms" > "$OUTPUT_FILE"

# Get list of policies
echo "Fetching available policies..."
POLICIES=$(curl -s "$API_URL/policies" | jq -r '.policies[]')

if [ -z "$POLICIES" ]; then
    echo "Error: Could not fetch policies from API"
    exit 1
fi

echo "Found policies: $(echo $POLICIES | tr '\n' ' ')"
echo ""

# Test each policy
for POLICY in $POLICIES; do
    echo "Testing policy: $POLICY"
    echo "-----------------------------------"

    # Apply policy
    echo "Applying policy..."
    APPLY_RESULT=$(curl -s -X POST "$API_URL/policy/apply" \
        -H "Content-Type: application/json" \
        -d "{\"policy\": \"$POLICY\"}")

    SUCCESS=$(echo "$APPLY_RESULT" | jq -r '.success // false')

    if [ "$SUCCESS" != "true" ]; then
        echo "Warning: Failed to apply policy $POLICY"
        echo "$POLICY,N/A,N/A,N/A,N/A,N/A,N/A" >> "$OUTPUT_FILE"
        continue
    fi

    # Wait for policy to take effect
    sleep 2

    # Run iperf3 test
    echo "Running iperf3 test..."
    IPERF_OUTPUT=$(docker exec iperf_client iperf3 -c 172.21.0.3 -t "$TEST_DURATION" -J 2>/dev/null || echo '{"error": true}')

    # Check if test succeeded
    if echo "$IPERF_OUTPUT" | jq -e '.error' > /dev/null 2>&1; then
        echo "Warning: iperf3 test failed for $POLICY"
        echo "$POLICY,ERROR,ERROR,ERROR,ERROR,ERROR,ERROR" >> "$OUTPUT_FILE"
        continue
    fi

    # Parse iperf3 JSON output
    BITRATE_SENDER=$(echo "$IPERF_OUTPUT" | jq -r '.end.sum_sent.bits_per_second // 0' | awk '{printf "%.2f", $1/1000000}')
    BITRATE_RECEIVER=$(echo "$IPERF_OUTPUT" | jq -r '.end.sum_received.bits_per_second // 0' | awk '{printf "%.2f", $1/1000000}')
    TRANSFER_SENDER=$(echo "$IPERF_OUTPUT" | jq -r '.end.sum_sent.bytes // 0' | awk '{printf "%.2f", $1/1000000}')
    TRANSFER_RECEIVER=$(echo "$IPERF_OUTPUT" | jq -r '.end.sum_received.bytes // 0' | awk '{printf "%.2f", $1/1000000}')
    RETRANSMITS=$(echo "$IPERF_OUTPUT" | jq -r '.end.sum_sent.retransmits // 0')

    # Calculate average RTT from intervals if available
    AVG_RTT=$(echo "$IPERF_OUTPUT" | jq -r '[.intervals[]?.streams[]?.rtt? // 0] | add / length' 2>/dev/null || echo "0")
    if [ "$AVG_RTT" = "null" ] || [ "$AVG_RTT" = "0" ]; then
        AVG_RTT="N/A"
    else
        AVG_RTT=$(printf "%.2f" "$AVG_RTT")
    fi

    # Write results to CSV
    echo "$POLICY,$BITRATE_SENDER,$BITRATE_RECEIVER,$TRANSFER_SENDER,$TRANSFER_RECEIVER,$RETRANSMITS,$AVG_RTT" >> "$OUTPUT_FILE"

    # Display results
    echo "  Sender Bitrate:   ${BITRATE_SENDER} Mbps"
    echo "  Receiver Bitrate: ${BITRATE_RECEIVER} Mbps"
    echo "  Sender Transfer:  ${TRANSFER_SENDER} MB"
    echo "  Receiver Transfer: ${TRANSFER_RECEIVER} MB"
    echo "  Retransmissions:  ${RETRANSMITS}"
    echo "  Avg RTT:          ${AVG_RTT} ms"
    echo ""

    # Clear policy before next test
    curl -s -X POST "$API_URL/policy/clear" > /dev/null
    sleep 2
done

echo "=================================="
echo "Testing complete!"
echo "Results saved to: $OUTPUT_FILE"
echo ""
echo "Summary:"
cat "$OUTPUT_FILE" | column -t -s ','

# Display formatted table
echo ""
echo "Formatted Results:"
echo "=================================="
cat "$OUTPUT_FILE" | awk -F',' 'NR==1 {print; print "-----------------------------------"} NR>1 {printf "%-20s %8s %8s %8s %8s %6s %8s\n", $1, $2, $3, $4, $5, $6, $7}'
