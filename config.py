"""Configuration settings for the application"""
import os
import json
from datetime import datetime

# File path for persistent storage
ORDERS_FILE = 'orders.json'
CONFIG_FILE = 'config.json'
LAST_UPDATES_FILE = 'app_data.json'
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

def get_auto_update_interval_hours():
    """Get the auto-update interval in hours from config (default: 6)"""
    config = load_config()
    return config.get('auto_update_interval_hours', 6)

def set_auto_update_interval_hours(hours):
    """Set the auto-update interval in hours in config"""
    config = load_config()
    config['auto_update_interval_hours'] = hours
    save_config(config)

def load_last_updates():
    """Load last update times from app_data.json"""
    if os.path.exists(LAST_UPDATES_FILE):
        try:
            with open(LAST_UPDATES_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            print(f"Error loading last updates: {e}")
            return {}
    
    # Migration: Check if old data exists in config.json and migrate it
    config = load_config()
    last_updates = {}
    migrated = False
    
    if 'cainiao_last_update' in config:
        last_updates['cainiao_last_update'] = config['cainiao_last_update']
        migrated = True
    if 'doar_last_update' in config:
        last_updates['doar_last_update'] = config['doar_last_update']
        migrated = True
    
    if migrated:
        save_last_updates(last_updates)
        # Remove from config.json
        if 'cainiao_last_update' in config:
            del config['cainiao_last_update']
        if 'doar_last_update' in config:
            del config['doar_last_update']
        save_config(config)
        print("Migrated last update times from config.json to app_data.json")
    
    return last_updates

def save_last_updates(last_updates):
    """Save last update times to separate file"""
    try:
        with open(LAST_UPDATES_FILE, 'w', encoding='utf-8') as f:
            json.dump(last_updates, f, indent=2, ensure_ascii=False)
    except IOError as e:
        print(f"Error saving last updates: {e}")

def get_cainiao_last_update():
    """Get the last Cainiao update time from app_data.json"""
    last_updates = load_last_updates()
    last_update_str = last_updates.get('cainiao_last_update', '')
    if last_update_str:
        try:
            return datetime.fromisoformat(last_update_str)
        except (ValueError, TypeError):
            return None
    return None

def set_cainiao_last_update(dt=None):
    """Set the last Cainiao update time in app_data.json"""
    last_updates = load_last_updates()
    if dt is None:
        dt = datetime.now()
    last_updates['cainiao_last_update'] = dt.isoformat()
    save_last_updates(last_updates)

def get_doar_last_update():
    """Get the last Doar Israel update time from app_data.json"""
    last_updates = load_last_updates()
    last_update_str = last_updates.get('doar_last_update', '')
    if last_update_str:
        try:
            return datetime.fromisoformat(last_update_str)
        except (ValueError, TypeError):
            return None
    return None

def set_doar_last_update(dt=None):
    """Set the last Doar Israel update time in app_data.json"""
    last_updates = load_last_updates()
    if dt is None:
        dt = datetime.now()
    last_updates['doar_last_update'] = dt.isoformat()
    save_last_updates(last_updates)

