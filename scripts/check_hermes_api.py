"""
Name: check_hermes_api.py
Description: Check Hermes API server health and readiness
Revision: 0.1.0
"""
import requests
import sys

def check_health():
    """Check if Hermes API server is healthy."""
    try:
        response = requests.get("http://localhost:8642/health", timeout=5)
        if response.status_code == 200:
            data = response.json()
            print(f"Hermes API: {data.get('status')} - {data.get('platform')}")
            return True
        else:
            print(f"ERROR: Health check returned {response.status_code}")
            return False
    except Exception as e:
        print(f"ERROR: Cannot reach Hermes API: {e}")
        return False

if __name__ == "__main__":
    sys.exit(0 if check_health() else 1)
