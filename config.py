"""Configuration settings for the application"""
import os
import json

# File path for persistent storage
ORDERS_FILE = 'orders.json'
CONFIG_FILE = 'config.json'
VERSION_FILE = 'VERSION'

# Directory for storing product images
IMAGES_DIR = os.path.join('static', 'images', 'products')
os.makedirs(IMAGES_DIR, exist_ok=True)

def load_config():
    """Load configuration from JSON file"""
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            print(f"Error loading config: {e}")
            return {}
    return {}

def save_config(config):
    """Save configuration to JSON file"""
    try:
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
    except IOError as e:
        print(f"Error saving config: {e}")

def get_doar_api_key():
    """Get Doar Israel API key from config"""
    config = load_config()
    return config.get('doar_israel_api_key', '')

def set_doar_api_key(api_key):
    """Set Doar Israel API key in config"""
    config = load_config()
    config['doar_israel_api_key'] = api_key
    save_config(config)

def get_app_version():
    """Read application version from VERSION file"""
    if os.path.exists(VERSION_FILE):
        try:
            with open(VERSION_FILE, 'r', encoding='utf-8') as f:
                return f.read().strip()
        except IOError as e:
            print(f"Error reading version file: {e}")
    return "0.00.00"

