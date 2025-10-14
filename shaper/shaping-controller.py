#!/usr/bin/env python3

from flask import Flask, request, jsonify
import subprocess
import json
import os

app = Flask(__name__)

current_policy = {"name": "none", "status": "inactive"}

def run_command(cmd):
    """Execute shell command and return result"""
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=10)
        return {"success": result.returncode == 0, "output": result.stdout, "error": result.stderr}
    except Exception as e:
        return {"success": False, "error": str(e)}

def clear_shaping(interface="eth1"):
    """Remove all traffic shaping rules"""
    run_command(f"tc qdisc del dev {interface} root 2>/dev/null || true")
    return {"status": "cleared", "interface": interface}

def apply_policy(policy_name, interface="eth1"):
    """Apply a traffic shaping policy"""
    global current_policy
    
    # Clear existing rules first
    clear_shaping(interface)
    
    # Handle no_shaping policy
    if policy_name == "no_shaping":
        current_policy = {"name": policy_name, "status": "active", "config": {"type": "none"}}
        return {"success": True, "policy": policy_name, "message": "No shaping applied"}
    
    # Load policies from file
    with open('/app/policies.json', 'r') as f:
        policies = json.load(f)
    
    if policy_name not in policies:
        return {"success": False, "error": f"Policy '{policy_name}' not found"}
    
    policy = policies[policy_name]
    
    # Apply the policy based on type
    if policy['type'] == 'cake':
        cmd = f"tc qdisc add dev {interface} root cake bandwidth {policy['bandwidth']}"
        if 'rtt' in policy:
            cmd += f" rtt {policy['rtt']}"
        if 'features' in policy:
            cmd += f" {' '.join(policy['features'])}"
    
    elif policy['type'] == 'netem':
        cmd = f"tc qdisc add dev {interface} root netem"
        if 'delay' in policy:
            cmd += f" delay {policy['delay']}"
        if 'jitter' in policy:
            cmd += f" {policy['jitter']}"
        if 'loss' in policy:
            cmd += f" loss {policy['loss']}"
        if 'rate' in policy:
            cmd += f" rate {policy['rate']}"
    
    elif policy['type'] == 'htb':
        commands = []
        commands.append(f"tc qdisc add dev {interface} root handle 1: htb default 30")
        commands.append(f"tc class add dev {interface} parent 1: classid 1:1 htb rate {policy['total_bandwidth']}")
        
        for i, class_cfg in enumerate(policy['classes'], start=10):
            classid = f"1:{i}"
            commands.append(f"tc class add dev {interface} parent 1:1 classid {classid} htb rate {class_cfg['rate']} ceil {class_cfg.get('ceil', class_cfg['rate'])}")
            commands.append(f"tc qdisc add dev {interface} parent {classid} handle {i}: fq_codel")
        
        for cmd in commands:
            result = run_command(cmd)
            if not result['success']:
                return {"success": False, "error": result['error'], "command": cmd}
        
        current_policy = {"name": policy_name, "status": "active", "config": policy}
        return {"success": True, "policy": policy_name, "type": "htb"}
    
    else:
        return {"success": False, "error": f"Unknown policy type: {policy['type']}"}
    
    # Execute the command
    result = run_command(cmd)
    
    if result['success']:
        current_policy = {"name": policy_name, "status": "active", "config": policy}
        return {"success": True, "policy": policy_name, "command": cmd}
    else:
        return {"success": False, "error": result['error'], "command": cmd}

@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint"""
    return jsonify({"status": "healthy", "current_policy": current_policy})

@app.route('/policies', methods=['GET'])
def list_policies():
    """List all available policies"""
    with open('/app/policies.json', 'r') as f:
        policies = json.load(f)
    return jsonify({"policies": list(policies.keys()), "details": policies})

@app.route('/policy/apply', methods=['POST'])
def apply_policy_endpoint():
    """Apply a traffic shaping policy"""
    data = request.json
    policy_name = data.get('policy')
    interface = data.get('interface', 'eth1')
    
    if not policy_name:
        return jsonify({"success": False, "error": "Policy name required"}), 400
    
    result = apply_policy(policy_name, interface)
    status_code = 200 if result.get('success', False) else 400
    return jsonify(result), status_code

@app.route('/policy/clear', methods=['POST'])
def clear_policy_endpoint():
    """Clear all traffic shaping"""
    global current_policy
    data = request.json or {}
    interface = data.get('interface', 'eth1')
    result = clear_shaping(interface)
    current_policy = {"name": "none", "status": "inactive"}
    return jsonify({"success": True, "result": result})

@app.route('/policy/current', methods=['GET'])
def get_current_policy():
    """Get currently applied policy"""
    tc_result = run_command("tc qdisc show dev eth1")
    return jsonify({
        "current_policy": current_policy,
        "tc_status": tc_result['output']
    })

@app.route('/stats', methods=['GET'])
def get_stats():
    """Get traffic statistics"""
    interface = request.args.get('interface', 'eth1')
    tc_stats = run_command(f"tc -s qdisc show dev {interface}")
    return jsonify({
        "interface": interface,
        "stats": tc_stats['output']
    })

if __name__ == '__main__':
    # Setup initial networking
    run_command("sysctl -w net.ipv4.ip_forward=1")
    run_command("iptables -t nat -A POSTROUTING -o eth1 -j MASQUERADE 2>/dev/null || true")
    run_command("iptables -A FORWARD -i eth0 -o eth1 -j ACCEPT 2>/dev/null || true")
    run_command("iptables -A FORWARD -i eth1 -o eth0 -m state --state RELATED,ESTABLISHED -j ACCEPT 2>/dev/null || true")
    
    print("Traffic Shaper Controller Starting...")
    print("Available at http://0.0.0.0:5000")
    app.run(host='0.0.0.0', port=5000, debug=False)