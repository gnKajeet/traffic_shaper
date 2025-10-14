#!/usr/bin/env python3

import requests
import subprocess
import json
import time
import csv
from datetime import datetime
import sys

class TrafficShapingTester:
    def __init__(self, shaper_api_url="http://localhost:5000", iperf_duration=30):
        self.shaper_api = shaper_api_url
        self.iperf_duration = iperf_duration
        self.results = []
        
    def get_policies(self):
        """Retrieve all available policies"""
        response = requests.get(f"{self.shaper_api}/policies")
        if response.status_code == 200:
            return response.json()['policies']
        else:
            raise Exception("Failed to retrieve policies")
    
    def apply_policy(self, policy_name):
        """Apply a traffic shaping policy"""
        print(f"  Applying policy: {policy_name}")
        response = requests.post(
            f"{self.shaper_api}/policy/apply",
            json={"policy": policy_name}
        )
        if response.status_code == 200:
            print(f"  ✓ Policy applied successfully")
            return True
        else:
            print(f"  ✗ Failed to apply policy: {response.text}")
            return False
    
    def clear_policy(self):
        """Clear all traffic shaping"""
        print("  Clearing traffic shaping...")
        requests.post(f"{self.shaper_api}/policy/clear")
    
    def run_iperf_test(self, test_name):
        """Run iperf3 test through the shaper"""
        print(f"  Running iperf3 test (duration: {self.iperf_duration}s)...")
        
        cmd = [
            "docker", "exec", "iperf_client",
            "iperf3", "-c", "172.21.0.3",
            "-t", str(self.iperf_duration),
            "-J"  # JSON output
        ]
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=self.iperf_duration + 10)
            
            if result.returncode == 0:
                data = json.loads(result.stdout)
                return self.parse_iperf_results(data, test_name)
            else:
                print(f"  ✗ iperf3 failed: {result.stderr}")
                return None
        except subprocess.TimeoutExpired:
            print(f"  ✗ iperf3 timed out")
            return None
        except json.JSONDecodeError as e:
            print(f"  ✗ Failed to parse iperf3 output: {e}")
            return None
    
    def parse_iperf_results(self, data, test_name):
        """Parse iperf3 JSON results"""
        try:
            end_data = data['end']
            sum_sent = end_data['sum_sent']
            sum_received = end_data['sum_received']
            
            result = {
                'test_name': test_name,
                'timestamp': datetime.now().isoformat(),
                'bandwidth_mbps': sum_received['bits_per_second'] / 1_000_000,
                'bytes_transferred': sum_sent['bytes'],
                'retransmits': sum_sent.get('retransmits', 0),
                'jitter_ms': sum_received.get('jitter_ms', 0),
                'lost_packets': sum_received.get('lost_packets', 0),
                'lost_percent': sum_received.get('lost_percent', 0),
                'duration': self.iperf_duration
            }
            
            print(f"  ✓ Bandwidth: {result['bandwidth_mbps']:.2f} Mbps")
            print(f"    Retransmits: {result['retransmits']}, Loss: {result['lost_percent']:.2f}%")
            
            return result
        except KeyError as e:
            print(f"  ✗ Error parsing results: {e}")
            return None
    
    def run_test_suite(self, policies=None, wait_between_tests=5):
        """Run tests for all policies"""
        if policies is None:
            policies = self.get_policies()
        
        print(f"\n{'='*60}")
        print(f"Starting test suite for {len(policies)} policies")
        print(f"iperf3 duration: {self.iperf_duration}s")
        print(f"{'='*60}\n")
        
        for i, policy in enumerate(policies, 1):
            print(f"\n[Test {i}/{len(policies)}] Policy: {policy}")
            print("-" * 60)
            
            # Apply policy
            if not self.apply_policy(policy):
                continue
            
            # Wait for policy to stabilize
            time.sleep(2)
            
            # Run iperf test
            result = self.run_iperf_test(policy)
            if result:
                self.results.append(result)
            
            # Clear policy after test
            self.clear_policy()
            
            # Wait between tests
            if i < len(policies):
                print(f"\n  Waiting {wait_between_tests}s before next test...")
                time.sleep(wait_between_tests)
        
        print(f"\n{'='*60}")
        print(f"Test suite completed: {len(self.results)}/{len(policies)} successful")
        print(f"{'='*60}\n")
    
    def save_results(self, filename="test_results.csv"):
        """Save results to CSV file"""
        if not self.results:
            print("No results to save")
            return
        
        with open(filename, 'w', newline='') as csvfile:
            fieldnames = ['test_name', 'timestamp', 'bandwidth_mbps', 'bytes_transferred',
                         'retransmits', 'jitter_ms', 'lost_packets', 'lost_percent', 'duration']
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            
            writer.writeheader()
            for result in self.results:
                writer.writerow(result)
        
        print(f"Results saved to {filename}")
    
    def print_summary(self):
        """Print summary of all test results"""
        if not self.results:
            print("No results to display")
            return
        
        print("\n" + "="*80)
        print("TEST SUMMARY")
        print("="*80)
        print(f"{'Policy':<25} {'Bandwidth':<15} {'Retrans':<10} {'Loss %':<10}")
        print("-"*80)
        
        for result in self.results:
            print(f"{result['test_name']:<25} "
                  f"{result['bandwidth_mbps']:>10.2f} Mbps  "
                  f"{result['retransmits']:>8}  "
                  f"{result['lost_percent']:>8.2f}%")
        
        print("="*80 + "\n")

def main():
    # Configuration
    SHAPER_API = "http://localhost:5000"
    IPERF_DURATION = 30  # seconds per test
    WAIT_BETWEEN_TESTS = 5  # seconds
    
    # Create tester
    tester = TrafficShapingTester(
        shaper_api_url=SHAPER_API,
        iperf_duration=IPERF_DURATION
    )
    
    # Check if shaper is available
    try:
        response = requests.get(f"{SHAPER_API}/health", timeout=5)
        if response.status_code != 200:
            print("Error: Traffic shaper API is not healthy")
            sys.exit(1)
    except requests.exceptions.RequestException as e:
        print(f"Error: Cannot connect to traffic shaper API at {SHAPER_API}")
        print(f"Make sure Docker containers are running: docker-compose up -d")
        sys.exit(1)
    
    # Run tests
    try:
        tester.run_test_suite(wait_between_tests=WAIT_BETWEEN_TESTS)
        
        # Display and save results
        tester.print_summary()
        tester.save_results("test_results.csv")
        
    except KeyboardInterrupt:
        print("\n\nTest interrupted by user")
        if tester.results:
            tester.print_summary()
            tester.save_results("test_results_partial.csv")
    except Exception as e:
        print(f"\nError during testing: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()