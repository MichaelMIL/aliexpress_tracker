"""Doar Israel tracking information fetching utilities"""
import requests
import json
from datetime import datetime
from config import get_doar_api_key

def parse_doar_tracking_response(data):
    """Parse Doar Israel API response into tracking_info dict"""
    tracking_info = {
        'status': 'Unknown',
        'events': [],
        'delivery_type': None,
        'last_update': datetime.now().isoformat()
    }
    
    if not isinstance(data, dict):
        return tracking_info
    
    # Extract current status from CategoryName
    category_name = data.get('CategoryName', '')
    if category_name:
        tracking_info['status'] = category_name
    
    # Extract delivery type
    delivery_type = data.get('DeliveryTypeDesc', '')
    if delivery_type:
        tracking_info['delivery_type'] = delivery_type
    
    # Extract tracking history from Maslul array
    maslul = data.get('Maslul', [])
    events = []
    
    if maslul and isinstance(maslul, list):
        for event in maslul:
            if isinstance(event, dict):
                status = event.get('Status', '')
                status_date = event.get('StatusDate', '')
                category_name = event.get('CategoryName', '')
                branch_name = event.get('BranchName', '')
                city = event.get('City', '')
                
                if status:
                    events.append({
                        'description': status,
                        'date': status_date,
                        'category': category_name,
                        'branch': branch_name,
                        'city': city
                    })
    
    # Reverse to show oldest first
    events.reverse()
    tracking_info['events'] = events
    
    # Extract Status field - use root Status if available, otherwise use latest from Maslul
    status_field = data.get('Status')
    if not status_field and events and len(events) > 0:
        # Get the most recent status from Maslul (last item after reverse)
        latest_event = events[-1] if events else None
        if latest_event and latest_event.get('description'):
            status_field = latest_event.get('description', '')
    
    if status_field:
        tracking_info['status_field'] = status_field
    
    # Extract latest update date
    if events:
        latest_event = events[-1]  # Most recent is last after reverse
        if latest_event.get('date'):
            tracking_info['last_update_date'] = latest_event['date']
    
    return tracking_info

def fetch_doar_tracking_info(tracking_number):
    """Fetch tracking information from Doar Israel API for a single tracking number"""
    print(f"Fetching Doar Israel tracking info for tracking number: {tracking_number}")
    if not tracking_number or not tracking_number.strip():
        return None
    
    api_key = get_doar_api_key()
    if not api_key:
        return {
            'status': 'Error',
            'events': [],
            'delivery_type': None,
            'last_update': datetime.now().isoformat(),
            'error': 'Doar Israel API key not configured'
        }
    
    try:
        tracking_number = tracking_number.strip()
        url = f"https://apimftprd.israelpost.co.il/MyPost-itemtrace/items/{tracking_number}/heb"
        
        headers = {
            'Ocp-Apim-Subscription-Key': api_key,
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'application/json',
        }
        
        # Increased timeout to 30 seconds for slow API responses
        response = requests.get(url, headers=headers, timeout=(10, 60))
        response.raise_for_status()
        
        data = response.json()
        return parse_doar_tracking_response(data)
        
    except requests.exceptions.Timeout as e:
        print(f"Timeout error fetching Doar Israel tracking info: {e}")
        return {
            'status': 'Error',
            'events': [],
            'delivery_type': None,
            'last_update': datetime.now().isoformat(),
            'error': 'Request timed out. The Doar Israel API is taking too long to respond. Please try again later.'
        }
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 401:
            return {
                'status': 'Error',
                'events': [],
                'delivery_type': None,
                'last_update': datetime.now().isoformat(),
                'error': 'Invalid API key'
            }
        elif e.response.status_code == 404:
            return {
                'status': 'Error',
                'events': [],
                'delivery_type': None,
                'last_update': datetime.now().isoformat(),
                'error': 'Tracking number not found'
            }
        else:
            return {
                'status': 'Error',
                'events': [],
                'delivery_type': None,
                'last_update': datetime.now().isoformat(),
                'error': f'HTTP {e.response.status_code}: {e.response.text[:100]}'
            }
    except requests.exceptions.ConnectionError as e:
        print(f"Connection error fetching Doar Israel tracking info: {e}")
        return {
            'status': 'Error',
            'events': [],
            'delivery_type': None,
            'last_update': datetime.now().isoformat(),
            'error': 'Connection error. Unable to reach Doar Israel API. Please check your internet connection.'
        }
    except json.JSONDecodeError as e:
        print(f"Error parsing JSON response from Doar Israel: {e}")
        return {
            'status': 'Error',
            'events': [],
            'delivery_type': None,
            'last_update': datetime.now().isoformat(),
            'error': 'Failed to parse tracking data'
        }
    except Exception as e:
        print(f"Error fetching Doar Israel tracking info: {e}")
        import traceback
        traceback.print_exc()
        return {
            'status': 'Error',
            'events': [],
            'delivery_type': None,
            'last_update': datetime.now().isoformat(),
            'error': str(e)
        }

