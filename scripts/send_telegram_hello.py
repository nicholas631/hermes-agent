"""
Name: send_telegram_hello.py
Description: Send a test "hello" message via Telegram bot API
Revision: 0.1.1
"""
import os
import requests
from pathlib import Path

# Import HERMES_HOME helper to support profiles
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))
from hermes_constants import get_hermes_home

def load_env():
    """Load environment variables from HERMES_HOME/.env"""
    env_file = get_hermes_home() / ".env"
    env_vars = {}
    
    if env_file.exists():
        with open(env_file, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    env_vars[key.strip()] = value.strip()
    
    return env_vars

def send_telegram_message(bot_token, chat_id, message):
    """Send a message using Telegram Bot API"""
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    
    payload = {
        "chat_id": chat_id,
        "text": message,
        "parse_mode": "Markdown"
    }
    
    try:
        response = requests.post(url, json=payload, timeout=10)
        response.raise_for_status()
        
        result = response.json()
        if result.get("ok"):
            print(f"SUCCESS: Message sent to chat {chat_id}")
            print(f"Message ID: {result['result']['message_id']}")
            return True
        else:
            print(f"ERROR: {result.get('description', 'Unknown error')}")
            return False
            
    except requests.exceptions.RequestException as e:
        print(f"ERROR: Failed to send message: {e}")
        return False

def main():
    print("=" * 60)
    print("Hermes Agent Telegram Hello Test")
    print("=" * 60)
    print()
    
    # Load configuration
    env_vars = load_env()
    bot_token = env_vars.get("TELEGRAM_BOT_TOKEN")
    chat_id = env_vars.get("TELEGRAM_ALLOWED_USERS")
    
    if not bot_token:
        print("ERROR: TELEGRAM_BOT_TOKEN not found in HERMES_HOME/.env")
        return 1
    
    if not chat_id:
        print("ERROR: TELEGRAM_ALLOWED_USERS not found in HERMES_HOME/.env")
        return 1
    
    print(f"Bot Token: {bot_token[:10]}...{bot_token[-5:]}")
    print(f"Chat ID: {chat_id}")
    print()
    
    # Send test message
    message = "Hello from Hermes Agent!\n\nThe Telegram gateway test is successful."
    
    print(f"Sending message: {message}")
    print()
    
    success = send_telegram_message(bot_token, chat_id, message)
    
    print()
    print("=" * 60)
    if success:
        print("TEST PASSED: Message delivered successfully")
        print("\nCheck your Telegram app to see the message!")
    else:
        print("TEST FAILED: Could not deliver message")
    print("=" * 60)
    
    return 0 if success else 1

if __name__ == "__main__":
    exit(main())
