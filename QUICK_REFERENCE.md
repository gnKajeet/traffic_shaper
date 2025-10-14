# Traffic Shaper Quick Reference

## Droplet Information
- **IP Address:** 137.184.194.112
- **Username:** root
- **Location:** /root/traffic_shaper

## SSH Access

```bash
# SSH into droplet
ssh root@137.184.194.112

# Create SSH tunnel for API access
ssh -f -N -L 5000:localhost:5000 root@137.184.194.112

# Check tunnel status
ps aux | grep "ssh.*5000:localhost:5000"

# Close tunnel
pkill -f "ssh.*5000:localhost:5000"
```

## API Commands (via SSH tunnel)

```bash
# Health check
curl http://localhost:5000/health | jq

# List all policies
curl http://localhost:5000/policies | jq '.policies'

# Apply a policy
curl -X POST http://localhost:5000/policy/apply \
  -H "Content-Type: application/json" \
  -d '{"policy": "mobile_4g"}' | jq

# Check current policy
curl http://localhost:5000/policy/current | jq

# Clear shaping
curl -X POST http://localhost:5000/policy/clear | jq

# Get traffic stats
curl http://localhost:5000/stats | jq
```

## Available Policies

- `no_shaping` - Baseline (no limits)
- `fiber_1gig` - 1 Gbps, 5ms latency (CAKE)
- `residential_cable` - 100 Mbps, 20ms latency (CAKE)
- `residential_dsl` - 25 Mbps, 40ms latency (CAKE)
- `mobile_5g` - 200 Mbps, 30ms ±10ms, 0.5% loss (netem)
- `mobile_4g` - 50 Mbps, 50ms ±20ms, 1% loss (netem)
- `mobile_3g` - 5 Mbps, 150ms ±50ms, 2% loss (netem)
- `satellite` - 25 Mbps, 600ms ±50ms, 0.5% loss (netem)
- `congested_network` - 10 Mbps, 100ms ±30ms, 5% loss (netem)
- `throttled_isp` - 5 Mbps, 50ms latency (CAKE)

## Docker Management (on droplet)

```bash
# View containers
docker-compose ps

# View logs
docker-compose logs -f

# Restart containers
docker-compose restart

# Stop containers
docker-compose down

# Rebuild and start
docker-compose up --build -d
```

## Testing

```bash
# Run iperf3 test (on droplet)
ssh root@137.184.194.112 "docker exec iperf_client iperf3 -c 172.21.0.3 -t 10"

# Quick test with specific policy
ssh root@137.184.194.112 "cd /root/traffic_shaper && ./quick_test.sh satellite"
```

## DigitalOcean Management

```bash
# List droplets
doctl compute droplet list

# Stop droplet
doctl compute droplet-action power-off 523526911

# Start droplet
doctl compute droplet-action power-on 523526911

# Destroy droplet (⚠️ permanent!)
doctl compute droplet delete 523526911
```

## Typical Workflow

```bash
# 1. Create SSH tunnel
ssh -f -N -L 5000:localhost:5000 root@137.184.194.112

# 2. Apply a policy
curl -X POST http://localhost:5000/policy/apply \
  -H "Content-Type: application/json" \
  -d '{"policy": "satellite"}' | jq

# 3. Verify it's applied
curl http://localhost:5000/policy/current | jq

# 4. Run a test
ssh root@137.184.194.112 "docker exec iperf_client iperf3 -c 172.21.0.3 -t 10"

# 5. Clear shaping when done
curl -X POST http://localhost:5000/policy/clear | jq

# 6. Close tunnel
pkill -f "ssh.*5000:localhost:5000"
```

## Troubleshooting

```bash
# Check if containers are running
ssh root@137.184.194.112 "docker-compose ps"

# View shaper logs
ssh root@137.184.194.112 "docker logs traffic_shaper"

# Check current tc rules
ssh root@137.184.194.112 "docker exec traffic_shaper tc qdisc show dev eth1"

# Restart everything
ssh root@137.184.194.112 "cd /root/traffic_shaper && docker-compose restart"
```

## Cost Information

- **Droplet:** $6/month (1GB RAM, 1 vCPU)
- **Remember to destroy when not in use to avoid charges**
