"""Configuration settings for the application"""
import os

# File path for persistent storage
ORDERS_FILE = 'orders.json'

# Directory for storing product images
IMAGES_DIR = os.path.join('static', 'images', 'products')
os.makedirs(IMAGES_DIR, exist_ok=True)

