"""Background scheduler for auto-updating tracking information"""
import threading
from datetime import datetime, timedelta
from models.order import orders, save_orders
from utils.tracking import fetch_bulk_tracking_info
from utils.doar_israel import fetch_doar_tracking_info
from config import (
    get_doar_api_key,
    get_auto_update_interval_hours,
    get_cainiao_last_update,
    set_cainiao_last_update,
    get_doar_last_update,
    set_doar_last_update
)

# Global state for next update time
_next_update_time = None
_update_lock = threading.Lock()
_current_timer = None

def get_next_update_time():
    """Get the next scheduled update time"""
    with _update_lock:
        return _next_update_time

def set_next_update_time(dt=None):
    """Set the next update time. If dt is None, sets it based on configured interval."""
    global _next_update_time
    with _update_lock:
        if dt is None:
            interval_hours = get_auto_update_interval_hours()
            _next_update_time = datetime.now() + timedelta(hours=interval_hours)
        else:
            _next_update_time = dt

def perform_auto_update():
    """Perform automatic update of both Cainiao and Doar Israel tracking"""
    print(f"[Auto-Update] Starting scheduled update at {datetime.now()}")
    
    try:
        # Update Cainiao tracking
        print("[Auto-Update] Updating Cainiao tracking...")
        orders_with_tracking = []
        skipped_delivered = 0
        
        for o in orders:
            if o.get('tracking_number') and o.get('tracking_number').strip():
                tracking_info = o.get('tracking_info') or {}
                status = tracking_info.get('status', '') if isinstance(tracking_info, dict) else ''
                if not status:
                    status = o.get('status', '')
                status_lower = status.lower() if status else ''
                
                if status_lower == 'delivered':
                    skipped_delivered += 1
                    continue
                
                orders_with_tracking.append(o)
        
        if orders_with_tracking:
            # Deduplicate tracking numbers to avoid duplicate API calls
            unique_tracking_numbers = list(set([o.get('tracking_number', '').strip() for o in orders_with_tracking if o.get('tracking_number', '').strip()]))
            print(f"[Auto-Update] Fetching Cainiao tracking for {len(unique_tracking_numbers)} unique tracking numbers (from {len(orders_with_tracking)} orders)")
            bulk_results = fetch_bulk_tracking_info(unique_tracking_numbers)
            
            updated = 0
            for order in orders_with_tracking:
                tracking_number = order.get('tracking_number', '').strip()
                if tracking_number and tracking_number in bulk_results:
                    tracking_info = bulk_results[tracking_number]
                    if tracking_info and not tracking_info.get('error'):
                        order['tracking_info'] = tracking_info
                        if tracking_info.get('status') and tracking_info['status'] != 'Unknown':
                            order['status'] = tracking_info['status']
                        if tracking_info.get('earliest_date') and not order.get('order_date'):
                            order['order_date'] = tracking_info['earliest_date']
                        updated += 1
            
            print(f"[Auto-Update] Cainiao: Updated {updated} out of {len(orders_with_tracking)} orders ({skipped_delivered} delivered skipped)")
            # Update last update time for Cainiao
            set_cainiao_last_update()
        
        # Update Doar Israel tracking
        print("[Auto-Update] Updating Doar Israel tracking...")
        api_key = get_doar_api_key()
        if api_key:
            orders_with_tracking = [o for o in orders if o.get('tracking_number') and o.get('tracking_number').strip()]
            
            if orders_with_tracking:
                # Deduplicate tracking numbers to avoid duplicate API calls
                unique_tracking_numbers = list(set([o.get('tracking_number', '').strip() for o in orders_with_tracking if o.get('tracking_number', '').strip()]))
                print(f"[Auto-Update] Fetching Doar Israel tracking for {len(unique_tracking_numbers)} unique tracking numbers (from {len(orders_with_tracking)} orders)")
                
                # Fetch tracking info once per unique tracking number
                tracking_results = {}
                for tracking_number in unique_tracking_numbers:
                    tracking_info = fetch_doar_tracking_info(tracking_number)
                    if tracking_info:
                        tracking_results[tracking_number] = tracking_info
                
                # Apply results to all orders with matching tracking numbers
                updated = 0
                for order in orders_with_tracking:
                    tracking_number = order.get('tracking_number', '').strip()
                    if tracking_number and tracking_number in tracking_results:
                        tracking_info = tracking_results[tracking_number]
                        if not tracking_info.get('error'):
                            if 'doar_tracking_info' not in order:
                                order['doar_tracking_info'] = {}
                            order['doar_tracking_info'] = tracking_info
                            updated += 1
                
                print(f"[Auto-Update] Doar Israel: Updated {updated} out of {len(orders_with_tracking)} orders")
                # Update last update time for Doar Israel
                set_doar_last_update()
            else:
                print("[Auto-Update] Doar Israel: No orders with tracking numbers found")
        else:
            print("[Auto-Update] Doar Israel: API key not configured, skipping")
        
        # Save orders after updates
        save_orders()
        print(f"[Auto-Update] Completed at {datetime.now()}")
        
    except Exception as e:
        print(f"[Auto-Update] Error during auto-update: {e}")
        import traceback
        traceback.print_exc()
    
    # Schedule next update
    set_next_update_time()
    schedule_next_update()

def schedule_next_update():
    """Schedule the next automatic update"""
    global _current_timer
    
    # Cancel existing timer if any
    if _current_timer:
        _current_timer.cancel()
    
    next_time = get_next_update_time()
    if not next_time:
        set_next_update_time()
        next_time = get_next_update_time()
    
    now = datetime.now()
    if next_time <= now:
        # If the time has passed, schedule for configured interval from now
        set_next_update_time()
        next_time = get_next_update_time()
    
    delay_seconds = (next_time - now).total_seconds()
    interval_hours = get_auto_update_interval_hours()
    print(f"[Auto-Update] Next update scheduled for {next_time} (in {delay_seconds/3600:.1f} hours, interval: {interval_hours}h)")
    
    # Create a timer thread
    _current_timer = threading.Timer(delay_seconds, perform_auto_update)
    _current_timer.daemon = True  # Allow program to exit even if timer is running
    _current_timer.start()
    
    return _current_timer

def start_scheduler():
    """Start the auto-update scheduler"""
    print("[Auto-Update] Starting scheduler...")
    set_next_update_time()
    schedule_next_update()
    print("[Auto-Update] Scheduler started")

