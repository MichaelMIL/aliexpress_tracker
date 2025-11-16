"""Order data model and storage functions"""
import json
import os
from config import ORDERS_FILE

# In-memory storage for orders
orders = []

def load_orders():
    """Load orders from JSON file"""
    global orders
    if os.path.exists(ORDERS_FILE):
        try:
            with open(ORDERS_FILE, 'r', encoding='utf-8') as f:
                loaded_orders = json.load(f)
                # Ensure all orders have integer IDs
                for order in loaded_orders:
                    if 'id' in order:
                        order['id'] = int(order['id'])
                # Clear and extend the existing list to preserve references
                orders.clear()
                orders.extend(loaded_orders)
                print(f"Loaded {len(orders)} orders from {ORDERS_FILE}")
        except (json.JSONDecodeError, IOError) as e:
            print(f"Error loading orders: {e}")
            orders.clear()
    else:
        orders.clear()
        print(f"Orders file {ORDERS_FILE} not found, starting with empty list")

def save_orders():
    """Save orders to JSON file"""
    try:
        with open(ORDERS_FILE, 'w', encoding='utf-8') as f:
            json.dump(orders, f, indent=2, ensure_ascii=False)
    except IOError as e:
        print(f"Error saving orders: {e}")

def get_next_order_id():
    """Get the next available order ID"""
    if not orders:
        return 1
    return max(order['id'] for order in orders) + 1

