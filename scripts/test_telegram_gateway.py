"""
Name: test_telegram_gateway.py
Description: Test script to verify Telegram gateway is operational
Revision: 0.1.1
"""
import os
import sys
from pathlib import Path

# Import HERMES_HOME helper to support profiles
sys.path.insert(0, str(Path(__file__).parent.parent))
from hermes_constants import get_hermes_home

def check_telegram_config():
    """Verify Telegram environment variables are set."""
    hermes_home = get_hermes_home()
    env_file = hermes_home / ".env"
    
    required = ["TELEGRAM_BOT_TOKEN"]
    auth_vars = ["TELEGRAM_ALLOWED_USERS", "GATEWAY_ALLOW_ALL_USERS", "TELEGRAM_ALLOW_ALL_USERS"]
    
    print("Checking Telegram configuration...")
    
    if not env_file.exists():
        print(f"ERROR: {env_file} not found")
        return False
    
    # Load .env file to check its contents
    env_vars = {}
    try:
        with open(env_file, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    env_vars[key.strip()] = value.strip()
    except Exception as e:
        print(f"ERROR: Could not read {env_file}: {e}")
        return False
    
    # Check for token
    has_token = "TELEGRAM_BOT_TOKEN" in env_vars and env_vars["TELEGRAM_BOT_TOKEN"]
    has_auth = any(var in env_vars and env_vars[var] for var in auth_vars)
    
    if not has_token:
        print("ERROR: TELEGRAM_BOT_TOKEN not set in .env file")
        return False
    
    print(f"  TELEGRAM_BOT_TOKEN: Found (length: {len(env_vars['TELEGRAM_BOT_TOKEN'])})")
    
    if not has_auth:
        print("WARNING: No user authorization configured (TELEGRAM_ALLOWED_USERS or GATEWAY_ALLOW_ALL_USERS)")
        print("         Only authorized users will receive responses")
    else:
        for var in auth_vars:
            if var in env_vars and env_vars[var]:
                print(f"  {var}: {env_vars[var]}")
    
    print("Configuration OK")
    return True

def check_gateway_running():
    """Check if gateway process is running."""
    import subprocess
    
    try:
        # Windows: check for python process running gateway
        result = subprocess.run(
            ["powershell", "-Command", "Get-Process python -ErrorAction SilentlyContinue | ForEach-Object { Get-CimInstance Win32_Process -Filter \"ProcessId = $($_.Id)\" | Select-Object CommandLine } | Where-Object { $_.CommandLine -like '*gateway*' }"],
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.stdout.strip():
            print("Gateway process detected:")
            print(f"  {result.stdout.strip()[:100]}...")
            return True
        else:
            print("No gateway process found")
            return False
    except Exception as e:
        print(f"Could not check gateway process: {e}")
        return False

def check_dependencies():
    """Check if required Python packages are installed."""
    print("\nChecking Python dependencies...")
    
    try:
        import telegram
        print(f"  python-telegram-bot: {telegram.__version__}")
        return True
    except ImportError:
        print("  ERROR: python-telegram-bot not installed")
        print("  Install with: pip install python-telegram-bot")
        return False

if __name__ == "__main__":
    print("=" * 60)
    print("Hermes Agent Telegram Gateway Test")
    print("=" * 60)
    print()
    
    deps_ok = check_dependencies()
    config_ok = check_telegram_config()
    gateway_running = check_gateway_running()
    
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    print(f"Dependencies: {'OK' if deps_ok else 'FAILED'}")
    print(f"Configuration: {'OK' if config_ok else 'FAILED'}")
    print(f"Gateway Running: {'YES' if gateway_running else 'NO'}")
    print("=" * 60)
    
    if deps_ok and config_ok:
        print("\nREADY: Configuration is valid")
        if not gateway_running:
            print("\nNext step: Start the gateway with 'hermes gateway'")
        else:
            print("\nGateway appears to be running")
        print("\nTest by sending a message to your bot on Telegram")
    else:
        print("\nNOT READY: Fix issues above")
    print("=" * 60)
