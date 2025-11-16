"""Tracking information fetching utilities"""
import requests
import json
from datetime import datetime

def parse_tracking_module(module):
    """Parse a single tracking module from the API response into tracking_info dict"""
    # Initialize tracking info
    tracking_info = {
        'status': 'Unknown',
        'events': [],
        'carrier': None,
        'last_update': datetime.now().isoformat()
    }
    
    if not isinstance(module, dict):
        return tracking_info
    
    # Get detailList first (needed for both status and latest update)
    detail_list = module.get('detailList', [])
    
    # Extract status from latestTrace or latest event's nodeDesc
    latest_trace = module.get('latestTrace', {})
    latest_group = latest_trace.get('group', {}) if isinstance(latest_trace, dict) else {}
    node_desc = latest_group.get('nodeDesc', '') if isinstance(latest_group, dict) else ''
    
    # If no nodeDesc in latestTrace, try to get from latest event
    if not node_desc and detail_list and len(detail_list) > 0:
        latest_event = detail_list[0]  # Most recent event is first
        event_group = latest_event.get('group', {})
        if isinstance(event_group, dict):
            node_desc = event_group.get('nodeDesc', '')
    
    # Fallback to statusDesc if nodeDesc not available
    if not node_desc:
        node_desc = module.get('statusDesc', '') or module.get('status', '')
    
    tracking_info['status'] = node_desc or 'Unknown'
    
    # Extract latest standerdDesc for the new column
    latest_standerd_desc = ''
    if detail_list and len(detail_list) > 0:
        latest_event = detail_list[0]
        latest_standerd_desc = latest_event.get('standerdDesc', '') or latest_event.get('desc', '')
    
    tracking_info['latest_standerd_desc'] = latest_standerd_desc
    
    # Extract carrier information (if available)
    carrier = module.get('carrier', '') or module.get('carrierName', '')
    if carrier:
        tracking_info['carrier'] = carrier
    
    # Extract origin and destination countries
    origin_country = module.get('originCountry', '')
    dest_country = module.get('destCountry', '')
    if origin_country and dest_country:
        tracking_info['carrier'] = f"{origin_country} → {dest_country}"
    
    # Extract tracking events from detailList
    events = []
    
    if detail_list:
        for event in detail_list:
            if isinstance(event, dict):
                standerd_desc = event.get('standerdDesc', '') or event.get('desc', '')
                
                if standerd_desc and standerd_desc.strip():
                    event_date = event.get('timeStr', '')
                    if not event_date and event.get('time'):
                        try:
                            timestamp = event.get('time') / 1000
                            event_date = datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d %H:%M:%S')
                        except:
                            event_date = None
                    
                    group = event.get('group', {})
                    group_desc = group.get('nodeDesc', '') if isinstance(group, dict) else ''
                    
                    events.append({
                        'description': standerd_desc.strip(),
                        'nodeDesc': group_desc,
                        'date': event_date
                    })
    
    events.reverse()
    tracking_info['events'] = events
    
    # Extract earliest and latest dates from events
    if events:
        event_times = []
        for event in detail_list:
            if isinstance(event, dict):
                timestamp = event.get('time')
                if timestamp:
                    event_times.append({
                        'timestamp': timestamp,
                        'timeStr': event.get('timeStr', '')
                    })
        
        if event_times:
            event_times.sort(key=lambda x: x['timestamp'])
            earliest = event_times[0]
            latest = event_times[-1]
            
            if earliest['timeStr']:
                tracking_info['earliest_date'] = earliest['timeStr']
            else:
                try:
                    timestamp = earliest['timestamp'] / 1000
                    tracking_info['earliest_date'] = datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d %H:%M:%S')
                except:
                    tracking_info['earliest_date'] = None
            
            if latest['timeStr']:
                tracking_info['last_update_date'] = latest['timeStr']
            else:
                try:
                    timestamp = latest['timestamp'] / 1000
                    tracking_info['last_update_date'] = datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d %H:%M:%S')
                except:
                    tracking_info['last_update_date'] = None
    
    return tracking_info

def fetch_tracking_info(tracking_number):
    """Fetch tracking information from Cainiao API for a single tracking number"""
    if not tracking_number or not tracking_number.strip():
        return None
    
    try:
        tracking_number = tracking_number.strip()
        url = f"https://global.cainiao.com/global/detail.json?mailNos={tracking_number}&lang=en-US&language=en-US"
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:144.0) Gecko/20100101 Firefox/144.0',
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate, br, zstd',
            'Connection': 'keep-alive',
            'Referer': f'https://global.cainiao.com/newDetail.htm?mailNoList={tracking_number}',
            'Sec-Fetch-Dest': 'empty',
            'Sec-Fetch-Mode': 'cors',
            'Sec-Fetch-Site': 'same-origin',
            'TE': 'trailers'
        }
        
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
        
        data = response.json()
        
        if isinstance(data, dict) and data.get('success'):
            module_list = data.get('module', [])
            
            if module_list and len(module_list) > 0:
                module = module_list[0]
                return parse_tracking_module(module)
        
        return None
        
    except json.JSONDecodeError as e:
        print(f"Error parsing JSON response: {e}")
        return {
            'status': 'Error',
            'events': [],
            'carrier': None,
            'last_update': datetime.now().isoformat(),
            'error': 'Failed to parse tracking data'
        }
    except Exception as e:
        print(f"Error fetching tracking info: {e}")
        import traceback
        traceback.print_exc()
        return {
            'status': 'Error',
            'events': [],
            'carrier': None,
            'last_update': datetime.now().isoformat(),
            'error': str(e)
        }

def fetch_bulk_tracking_info(tracking_numbers):
    """Fetch tracking information for multiple tracking numbers in a single API call"""
    if not tracking_numbers:
        return {}
    
    valid_tracking_numbers = [tn.strip() for tn in tracking_numbers if tn and tn.strip()]
    
    if not valid_tracking_numbers:
        return {}
    
    try:
        mail_nos = ','.join(valid_tracking_numbers)
        referer_mail_nos = '%2C'.join(valid_tracking_numbers)
        
        url = f"https://global.cainiao.com/global/detail.json?mailNos={mail_nos}&lang=en-US&language=en-US"
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:144.0) Gecko/20100101 Firefox/144.0',
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate, br, zstd',
            'Connection': 'keep-alive',
            'Referer': f'https://global.cainiao.com/newDetail.htm?mailNoList={referer_mail_nos}&otherMailNoList=',
            'bx-v': '2.5.31',
            'Sec-Fetch-Dest': 'empty',
            'Sec-Fetch-Mode': 'cors',
            'Sec-Fetch-Site': 'same-origin',
            'Priority': 'u=0',
            'TE': 'trailers'
        }
        
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        
        data = response.json()
        
        results = {}
        
        if isinstance(data, dict) and data.get('success'):
            module_list = data.get('module', [])
            
            for module in module_list:
                if isinstance(module, dict):
                    mail_no = module.get('mailNo', '')
                    if mail_no:
                        tracking_info = parse_tracking_module(module)
                        results[mail_no] = tracking_info
        
        return results
        
    except json.JSONDecodeError as e:
        print(f"Error parsing JSON response for bulk tracking: {e}")
        return {}
    except Exception as e:
        print(f"Error fetching bulk tracking info: {e}")
        import traceback
        traceback.print_exc()
        return {}

