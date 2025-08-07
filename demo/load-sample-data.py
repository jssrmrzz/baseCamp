#!/usr/bin/env python3
"""
Load sample scenarios into baseCamp demo instance
"""

import argparse
import json
import requests
import time
from pathlib import Path


def load_scenarios(demo_url: str, scenarios_file: Path):
    """Load scenarios via API."""
    with open(scenarios_file, 'r') as f:
        data = json.load(f)
    
    print(f"Loading {len(data['scenarios'])} scenarios for {data['display_name']}")
    
    for scenario in data['scenarios']:
        print(f"  Processing: {scenario['name']}")
        
        payload = {
            'message': scenario['message'],
            'contact': scenario['contact'],
            'source': 'demo_scenario'
        }
        
        try:
            response = requests.post(f"{demo_url}/api/v1/intake", json=payload, timeout=30)
            if response.status_code == 201:
                result = response.json()
                print(f"    ✅ Created lead: {result.get('lead_id')}")
            else:
                print(f"    ❌ Failed: {response.status_code} - {response.text}")
        except Exception as e:
            print(f"    ❌ Error: {e}")
        
        time.sleep(2)  # Rate limiting


def main():
    parser = argparse.ArgumentParser(description='Load demo scenarios')
    parser.add_argument('--demo-url', required=True, help='Demo instance URL')
    parser.add_argument('--scenarios', required=True, type=Path, help='Scenarios JSON file')
    
    args = parser.parse_args()
    
    load_scenarios(args.demo_url, args.scenarios)


if __name__ == '__main__':
    main()
