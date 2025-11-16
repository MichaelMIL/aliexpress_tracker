from flask import Flask, render_template, request, jsonify, Response, send_from_directory
import requests
from bs4 import BeautifulSoup
import re
import json
import os
from datetime import datetime
import hashlib
from urllib.parse import urlparse

app = Flask(__name__)

# File path for persistent storage
ORDERS_FILE = 'orders.json'

# Directory for storing product images
IMAGES_DIR = os.path.join('static', 'images', 'products')
os.makedirs(IMAGES_DIR, exist_ok=True)

# In-memory storage for orders
orders = []

def load_orders():
    """Load orders from JSON file"""
    global orders
    if os.path.exists(ORDERS_FILE):
        try:
            with open(ORDERS_FILE, 'r', encoding='utf-8') as f:
                orders = json.load(f)
                # Ensure all orders have integer IDs
                for order in orders:
                    if 'id' in order:
                        order['id'] = int(order['id'])
        except (json.JSONDecodeError, IOError) as e:
            print(f"Error loading orders: {e}")
            orders = []
    else:
        orders = []

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

def is_mostly_english(text):
    """Check if text is mostly English (ASCII) characters"""
    if not text:
        return False
    
    # Remove common punctuation and numbers for better detection
    text_clean = re.sub(r'[0-9\s\-_.,;:!?()\[\]{}"\']+', '', text)
    if len(text_clean) < 3:  # If after cleaning it's too short, it's probably not meaningful
        return False
    
    # Check for meaningful English words (at least 3 letters)
    sample = text[:200] if len(text) > 200 else text
    ascii_letters = sum(1 for c in sample if c.isalpha() and ord(c) < 128)
    total_chars = len([c for c in sample if c.isalnum() or c.isspace()])
    
    if total_chars == 0:
        return False
    
    # At least 70% should be ASCII letters, and we need at least some letters
    return ascii_letters > total_chars * 0.5 and ascii_letters >= 5

def download_and_save_image(image_url, product_id=None):
    """Download an image from URL and save it locally. Returns the local path or None if failed."""
    if not image_url:
        return None
    
    try:
        # Generate a filename based on URL hash and product ID
        url_hash = hashlib.md5(image_url.encode()).hexdigest()[:12]
        
        # Determine file extension from URL
        parsed_url = urlparse(image_url)
        path = parsed_url.path
        ext = '.jpg'  # default
        if '.jpg' in path.lower() or '.jpeg' in path.lower():
            ext = '.jpg'
        elif '.png' in path.lower():
            ext = '.png'
        elif '.webp' in path.lower():
            ext = '.webp'
        elif '.avif' in path.lower():
            ext = '.jpg'  # Convert avif to jpg for compatibility
        
        # Create filename: product_id_hash.ext or just hash.ext
        if product_id:
            filename = f"{product_id}_{url_hash}{ext}"
        else:
            filename = f"{url_hash}{ext}"
        
        local_path = os.path.join(IMAGES_DIR, filename)
        
        # If image already exists, return the path
        if os.path.exists(local_path):
            return f"/static/images/products/{filename}"
        
        # Download the image
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Referer': 'https://www.aliexpress.com/',
            'Accept': 'image/avif,image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9',
        }
        
        # Try multiple URL variations if needed
        urls_to_try = [image_url]
        
        # If it's an optimized _220x220q75.jpg that might not exist, try original .jpg
        if '_220x220q75.jpg' in image_url and 'alicdn.com' in image_url:
            original_url = image_url.replace('_220x220q75.jpg', '.jpg')
            urls_to_try.insert(0, original_url)
        
        for url_to_try in urls_to_try:
            try:
                response = requests.get(url_to_try, headers=headers, timeout=10, stream=True)
                if response.status_code == 200:
                    # Save the image
                    with open(local_path, 'wb') as f:
                        for chunk in response.iter_content(chunk_size=8192):
                            f.write(chunk)
                    
                    print(f"Saved image to {local_path}")
                    return f"/static/images/products/{filename}"
                elif response.status_code == 404:
                    continue  # Try next URL
                else:
                    response.raise_for_status()
            except requests.exceptions.HTTPError as e:
                if e.response.status_code == 404:
                    continue
                else:
                    print(f"Error downloading image {url_to_try}: {e}")
            except Exception as e:
                print(f"Error downloading image {url_to_try}: {e}")
                continue
        
        print(f"Failed to download image after trying {len(urls_to_try)} URLs: {image_url}")
        return None
        
    except Exception as e:
        print(f"Error in download_and_save_image: {e}")
        import traceback
        traceback.print_exc()
        return None

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
    # The API doesn't seem to provide carrier name directly, but we can check
    carrier = module.get('carrier', '') or module.get('carrierName', '')
    if carrier:
        tracking_info['carrier'] = carrier
    
    # Extract origin and destination countries
    origin_country = module.get('originCountry', '')
    dest_country = module.get('destCountry', '')
    if origin_country and dest_country:
        tracking_info['carrier'] = f"{origin_country} → {dest_country}"
    
    # Extract tracking events from detailList (already retrieved above)
    events = []
    
    if detail_list:
        for event in detail_list:
            if isinstance(event, dict):
                # Get standerdDesc (note: API has typo "standerd" instead of "standard")
                standerd_desc = event.get('standerdDesc', '') or event.get('desc', '')
                
                if standerd_desc and standerd_desc.strip():
                    # Extract date - prefer timeStr (formatted) over time (timestamp)
                    event_date = event.get('timeStr', '')
                    if not event_date and event.get('time'):
                        # Convert timestamp to readable date if needed
                        try:
                            timestamp = event.get('time') / 1000  # Convert from milliseconds
                            event_date = datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d %H:%M:%S')
                        except:
                            event_date = None
                    
                    # Get group description (nodeDesc)
                    group = event.get('group', {})
                    group_desc = group.get('nodeDesc', '') if isinstance(group, dict) else ''
                    
                    events.append({
                        'description': standerd_desc.strip(),
                        'nodeDesc': group_desc,
                        'date': event_date
                    })
    
    # Sort events by time (most recent first) - detailList should already be sorted
    # But we'll reverse it to show most recent first
    events.reverse()
    tracking_info['events'] = events
    
    # Extract earliest and latest dates from events
    if events:
        # Get all dates (both timeStr and timestamps)
        event_times = []
        for event in detail_list:
            if isinstance(event, dict):
                # Try to get timestamp first (more reliable for sorting)
                timestamp = event.get('time')
                if timestamp:
                    event_times.append({
                        'timestamp': timestamp,
                        'timeStr': event.get('timeStr', '')
                    })
        
        if event_times:
            # Sort by timestamp to find earliest and latest
            event_times.sort(key=lambda x: x['timestamp'])
            earliest = event_times[0]
            latest = event_times[-1]
            
            # Store earliest date (for order_date)
            if earliest['timeStr']:
                tracking_info['earliest_date'] = earliest['timeStr']
            else:
                try:
                    timestamp = earliest['timestamp'] / 1000
                    tracking_info['earliest_date'] = datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d %H:%M:%S')
                except:
                    tracking_info['earliest_date'] = None
            
            # Store latest date (for last_update)
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
        
        # Parse the JSON response
        # The response structure: { "module": [{ ... }], "success": true }
        if isinstance(data, dict) and data.get('success'):
            module_list = data.get('module', [])
            
            if module_list and len(module_list) > 0:
                module = module_list[0]  # Get first tracking module
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
    
    # Filter out empty tracking numbers
    valid_tracking_numbers = [tn.strip() for tn in tracking_numbers if tn and tn.strip()]
    
    if not valid_tracking_numbers:
        return {}
    
    try:
        # Join tracking numbers with commas
        mail_nos = ','.join(valid_tracking_numbers)
        # URL encode the tracking numbers for the Referer header
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
        
        # Result dictionary: tracking_number -> tracking_info
        results = {}
        
        # Parse the JSON response
        # The response structure: { "module": [{ ... }], "success": true }
        if isinstance(data, dict) and data.get('success'):
            module_list = data.get('module', [])
            
            # Map each module to its tracking number
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

def extract_product_info(aliexpress_url):
    """Extract product information from AliExpress URL"""
    try:
        # Extract product ID first (before URL modification)
        product_id = None
        id_match = re.search(r'/(\d+)\.html', aliexpress_url)
        if id_match:
            product_id = id_match.group(1)
        
        # Try multiple URL variations
        urls_to_try = []
        
        # 1. Normalized www.aliexpress.com with lang=en
        normalized_url = aliexpress_url
        # Normalize domain to www.aliexpress.com for better compatibility
        normalized_url = re.sub(r'https?://([a-z]{2}\.)?aliexpress\.com', r'https://www.aliexpress.com', normalized_url, flags=re.IGNORECASE)
        # Remove tracking parameters
        normalized_url = re.sub(r'[&?]lang=[^&]*', '', normalized_url)
        normalized_url = re.sub(r'[&?]gatewayAdapt=[^&]*', '', normalized_url)
        normalized_url = re.sub(r'[&?]spm=[^&]*', '', normalized_url)
        # Add language parameter
        separator = '&' if '?' in normalized_url else '?'
        urls_to_try.append(f"{normalized_url}{separator}lang=en")
        
        # 2. Original URL (in case normalization breaks it)
        urls_to_try.append(aliexpress_url)
        
        # 3. Simple www version without parameters
        simple_url = re.sub(r'https?://([a-z]{2}\.)?aliexpress\.com', r'https://www.aliexpress.com', aliexpress_url, flags=re.IGNORECASE)
        simple_url = re.sub(r'\?.*$', '', simple_url)  # Remove all query parameters
        urls_to_try.append(f"{simple_url}?lang=en")
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Cache-Control': 'no-cache',
            'Referer': 'https://www.aliexpress.com/'
        }
        
        response = None
        url = None
        for attempt_url in urls_to_try:
            try:
                print(f"Trying URL: {attempt_url}")
                response = requests.get(attempt_url, headers=headers, timeout=15, allow_redirects=True)
                if response.status_code == 200 and len(response.content) > 1000:  # Make sure we got actual content
                    url = attempt_url
                    break
            except Exception as e:
                print(f"Failed to fetch {attempt_url}: {e}")
                continue
        
        if not response or response.status_code != 200:
            raise Exception(f"Failed to fetch product page. Tried {len(urls_to_try)} URL variations.")
        
        response.raise_for_status()
        
        # Check if we got meaningful content
        if len(response.content) < 500:
            raise Exception("Received empty or very short response from AliExpress")
        
        soup = BeautifulSoup(response.content, 'html.parser')
        html_text = response.text
        
        # Debug: Print page title to see what we got
        page_title = soup.find('title')
        if page_title:
            print(f"Page title: {page_title.get_text()[:100]}")
        
        # Extract product title - try multiple methods
        title = None
        
        # Method 1: Try meta tags first (most reliable)
        meta_selectors = [
            ('meta', {'property': 'og:title'}),
            ('meta', {'name': 'twitter:title'}),
            ('meta', {'property': 'twitter:title'}),
            ('meta', {'itemprop': 'name'})
        ]
        for tag, attrs in meta_selectors:
            meta_elem = soup.find(tag, attrs)
            if meta_elem and meta_elem.get('content'):
                candidate_title = meta_elem.get('content').strip()
                # Clean up common AliExpress suffixes
                candidate_title = re.sub(r'\s*-\s*AliExpress.*$', '', candidate_title, flags=re.IGNORECASE)
                # Prefer English titles
                if candidate_title and is_mostly_english(candidate_title):
                    title = candidate_title
                    break
                elif not title:  # Keep as fallback if no English found
                    title = candidate_title
        
        # Method 2: Try to extract from JSON-LD structured data
        if not title or not is_mostly_english(title):
            json_ld_scripts = soup.find_all('script', type='application/ld+json')
            english_title = None
            fallback_title = None
            for script in json_ld_scripts:
                try:
                    data = json.loads(script.string)
                    if isinstance(data, dict):
                        # Look for English-specific fields first
                        if 'name' in data:
                            candidate = data['name'].strip()
                            if is_mostly_english(candidate):
                                english_title = candidate
                            elif not fallback_title:
                                fallback_title = candidate
                        # Check for multi-language structure
                        if 'name' in data and isinstance(data['name'], dict):
                            if 'en' in data['name']:
                                english_title = data['name']['en'].strip()
                            elif 'en_US' in data['name']:
                                english_title = data['name']['en_US'].strip()
                        elif '@graph' in data:
                            for item in data['@graph']:
                                if isinstance(item, dict) and item.get('@type') == 'Product':
                                    if 'name' in item:
                                        candidate = item['name'].strip() if isinstance(item['name'], str) else None
                                        if candidate:
                                            if is_mostly_english(candidate):
                                                english_title = candidate
                                            elif not fallback_title:
                                                fallback_title = candidate
                                    # Check for multi-language name
                                    if 'name' in item and isinstance(item['name'], dict):
                                        if 'en' in item['name']:
                                            english_title = item['name']['en'].strip()
                                        elif 'en_US' in item['name']:
                                            english_title = item['name']['en_US'].strip()
                    if english_title:
                        break
                except (json.JSONDecodeError, KeyError, TypeError):
                    continue
            if english_title:
                title = english_title
            elif fallback_title and not title:
                title = fallback_title
        
        # Method 3: Try to extract from window.runParams or similar script tags
        if not title or not is_mostly_english(title):
            scripts = soup.find_all('script')
            for script in scripts:
                if script.string:
                    script_text = script.string
                    
                    # Try to find window.runParams with product data
                    # Look for the full runParams structure - use a more robust approach
                    # First try to find the start of runParams
                    runparams_start = script_text.find('window.runParams')
                    if runparams_start != -1:
                        # Find the opening brace
                        brace_start = script_text.find('{', runparams_start)
                        if brace_start != -1:
                            # Try to find matching closing brace (simplified - count braces)
                            brace_count = 0
                            brace_end = brace_start
                            for i in range(brace_start, min(brace_start + 50000, len(script_text))):  # Limit search
                                if script_text[i] == '{':
                                    brace_count += 1
                                elif script_text[i] == '}':
                                    brace_count -= 1
                                    if brace_count == 0:
                                        brace_end = i + 1
                                        break
                            
                            if brace_end > brace_start:
                                try:
                                    runparams_json = script_text[brace_start:brace_end]
                                    # Try to parse as JSON
                                    runparams_data = json.loads(runparams_json)
                                    # Look for subject or title in various places
                                    if isinstance(runparams_data, dict):
                                        # Check for subject directly
                                        if 'subject' in runparams_data:
                                            candidate = str(runparams_data['subject']).strip()
                                            if candidate and is_mostly_english(candidate) and len(candidate) > 10:
                                                title = candidate
                                                break
                                        # Check for data structure
                                        if 'data' in runparams_data:
                                            data = runparams_data['data']
                                            if isinstance(data, dict):
                                                if 'subject' in data:
                                                    candidate = str(data['subject']).strip()
                                                    if candidate and is_mostly_english(candidate) and len(candidate) > 10:
                                                        title = candidate
                                                        break
                                            elif isinstance(data, list) and len(data) > 0:
                                                # Sometimes data is a list
                                                for item in data:
                                                    if isinstance(item, dict) and 'subject' in item:
                                                        candidate = str(item['subject']).strip()
                                                        if candidate and is_mostly_english(candidate) and len(candidate) > 10:
                                                            title = candidate
                                                            break
                                                    if title:
                                                        break
                                except (json.JSONDecodeError, ValueError) as e:
                                    # If JSON parsing fails, try regex approach
                                    pass
                    
                    # Try to find English title in multi-language data structures
                    # Look for "en" or "en_US" language keys
                    en_title_match = re.search(r'"(?:en|en_US|en-US)"\s*:\s*\{[^}]*"(?:subject|title|name)"\s*:\s*"([^"]+)"', script_text)
                    if not en_title_match:
                        # Look for English in translations object
                        en_title_match = re.search(r'"translations"\s*:\s*\{[^}]*"en"[^}]*"(?:subject|title|name)"\s*:\s*"([^"]+)"', script_text)
                    if not en_title_match:
                        # Look for product title in window.runParams (English version) - more specific pattern
                        en_title_match = re.search(r'window\.runParams\s*=\s*\{[^}]*"subject"\s*:\s*"([^"]+)"', script_text)
                    if not en_title_match:
                        # Look for subject in data structure
                        en_title_match = re.search(r'"data"\s*:\s*\{[^}]*"subject"\s*:\s*"([^"]+)"', script_text)
                    if not en_title_match:
                        # Generic subject/title search - but only if it looks English
                        subject_matches = re.findall(r'"subject"\s*:\s*"([^"]+)"', script_text)
                        for match in subject_matches:
                            candidate = match.strip()
                            # Unescape
                            candidate = candidate.replace('\\u0026', '&').replace('\\/', '/')
                            try:
                                candidate = candidate.encode().decode('unicode_escape') if '\\u' in candidate else candidate
                            except:
                                pass
                            if candidate and is_mostly_english(candidate) and len(candidate) > 10:
                                en_title_match = type('obj', (object,), {'group': lambda x: candidate})()
                                break
                    if not en_title_match:
                        en_title_match = re.search(r'"productTitle"\s*:\s*"([^"]+)"', script_text)
                    if not en_title_match:
                        en_title_match = re.search(r'"title"\s*:\s*"([^"]+)"', script_text)
                    
                    if en_title_match:
                        candidate_title = en_title_match.group(1).strip()
                        # Unescape common HTML entities and Unicode
                        candidate_title = candidate_title.replace('\\u0026', '&').replace('\\/', '/')
                        try:
                            candidate_title = candidate_title.encode().decode('unicode_escape') if '\\u' in candidate_title else candidate_title
                        except:
                            pass
                        # Only accept English titles
                        if candidate_title and is_mostly_english(candidate_title) and len(candidate_title) > 10:
                            title = candidate_title
                            break
                        elif not title and len(candidate_title) > 10:  # Keep as fallback only if no title yet
                            title = candidate_title
        
        # Method 4: Try CSS selectors
        if not title:
            title_selectors = [
                'h1[data-pl="product-title"]',
                'h1.product-title-text',
                'h1[class*="product-title"]',
                'h1[class*="ProductTitle"]',
                'h1.product-title',
                'h1',
                '[data-pl="product-title"]',
                '.product-title-text'
            ]
            for selector in title_selectors:
                title_elem = soup.select_one(selector)
                if title_elem:
                    title = title_elem.get_text(strip=True)
                    if title and len(title) > 5:  # Make sure it's not just whitespace
                        break
        
        # Method 5: Extract from page title tag and clean it
        if not title or not is_mostly_english(title) or len(title) < 10:
            title_tag = soup.find('title')
            if title_tag:
                candidate_title = title_tag.get_text(strip=True)
                # Remove common AliExpress suffixes
                candidate_title = re.sub(r'\s*-\s*AliExpress.*$', '', candidate_title, flags=re.IGNORECASE)
                candidate_title = re.sub(r'\s*\|\s*AliExpress.*$', '', candidate_title, flags=re.IGNORECASE)
                # Only accept if it's English and meaningful length
                if candidate_title and is_mostly_english(candidate_title) and len(candidate_title) > 10:
                    title = candidate_title
                elif not title and len(candidate_title) > 10:
                    # Last resort - but still prefer English
                    title = candidate_title
        
        # Extract product image - FIRST PRIORITY: og:image meta tag
        image_url = None
        print(f"\n=== IMAGE EXTRACTION DEBUG for {aliexpress_url} ===")
        
        # FIRST PRIORITY: Get image from og:image meta tag (most reliable)
        og_image = soup.find('meta', {'property': 'og:image'})
        print(f"1. Checking og:image meta tag...")
        if og_image:
            candidate = og_image.get('content')
            print(f"   Found og:image content: {candidate[:100] if candidate else 'None'}...")
            if candidate:
                candidate = candidate.strip()
                original_candidate = candidate
                # Handle relative URLs
                if candidate.startswith('//'):
                    candidate = 'https:' + candidate
                    print(f"   Converted // to https: {candidate[:100]}...")
                elif candidate.startswith('/'):
                    candidate = 'https://www.aliexpress.com' + candidate
                    print(f"   Converted / to full URL: {candidate[:100]}...")
                if candidate.startswith('http'):
                    # Skip thumbnails
                    if '50x50' not in candidate and '60x60' not in candidate and '80x80' not in candidate:
                        image_url = candidate
                        print(f"   ✓ SELECTED og:image: {image_url[:150]}...")
                    else:
                        print(f"   ✗ Rejected og:image (thumbnail): {candidate[:100]}...")
                else:
                    print(f"   ✗ Rejected og:image (not http): {candidate[:100]}...")
        else:
            print(f"   ✗ No og:image meta tag found")
        
        # SECOND PRIORITY: Try other meta tags
        if not image_url:
            print(f"2. Checking other meta tags...")
            image_selectors = [
                ('meta', {'name': 'twitter:image'}),
                ('meta', {'property': 'twitter:image'}),
                ('meta', {'itemprop': 'image'})
            ]
            for tag, attrs in image_selectors:
                img_elem = soup.find(tag, attrs)
                if img_elem and img_elem.get('content'):
                    candidate = img_elem.get('content').strip()
                    print(f"   Found {tag} {attrs}: {candidate[:100] if candidate else 'None'}...")
                    if candidate:
                        if candidate.startswith('//'):
                            candidate = 'https:' + candidate
                        elif candidate.startswith('/'):
                            candidate = 'https://www.aliexpress.com' + candidate
                        if candidate.startswith('http'):
                            # Skip thumbnails
                            if '50x50' not in candidate and '60x60' not in candidate and '80x80' not in candidate:
                                image_url = candidate
                                print(f"   ✓ SELECTED {tag} {attrs}: {image_url[:150]}...")
                                break
                            else:
                                print(f"   ✗ Rejected (thumbnail): {candidate[:100]}...")
        else:
            print(f"2. Skipping other meta tags (already found image)")
        
        # THIRD PRIORITY: Try CSS selectors (most accurate for getting the main product image)
        if not image_url:
            print(f"3. Checking CSS selectors...")
            image_candidates = []
            specific_selectors = [
                'html body.unfoldShopCart.pdp-new-pc div#root div.pdp-page-wrap div.pdp-body.pdp-wrap div.pdp-body-top div.pdp-body-top-left div.pdp-info div.pdp-info-left div.main-image--wrap--nFuR5UU div.image-view-v2--wrap--N4InOxs div.slider--wrap--dfLgmYD div.slider--slider--VKj5hty div div.slider--item--RpyeewA div.slider--img--kD4mIg7 img',
                'div.main-image--wrap--nFuR5UU div.slider--img--kD4mIg7 img',
                'div.slider--img--kD4mIg7 img',
                'div.image-view-v2--wrap--N4InOxs img',
                'div.pdp-info-left div.main-image--wrap--nFuR5UU img',
                'div.pdp-info-left img',
            ]
            
            for i, selector in enumerate(specific_selectors):
                try:
                    img_elems = soup.select(selector)
                    print(f"   Selector {i+1} ({selector[:50]}...): Found {len(img_elems)} elements")
                    # Get the first image (main product image, not thumbnails)
                    if img_elems:
                        img_elem = img_elems[0]  # First one is usually the main image
                        # Try multiple attributes in order of preference
                        for attr in ['data-zoom', 'data-zoom-image', 'data-src-main', 'src', 'data-src', 'data-lazy-src']:
                            candidate = img_elem.get(attr)
                            if candidate:
                                print(f"      Found {attr}: {candidate[:100]}...")
                                if candidate.startswith('//'):
                                    candidate = 'https:' + candidate
                                elif candidate.startswith('/'):
                                    candidate = 'https://www.aliexpress.com' + candidate
                                if candidate.startswith('http') and any(ext in candidate for ext in ['.jpg', '.jpeg', '.png', '.webp', '.avif']):
                                    # Skip thumbnails (usually have "50x50" or "60x60" in URL)
                                    if '50x50' not in candidate and '60x60' not in candidate and '80x80' not in candidate:
                                        image_candidates.append(('css_' + selector[:30], candidate))
                                        print(f"      ✓ Added candidate: {candidate[:150]}...")
                                        break
                                    else:
                                        print(f"      ✗ Rejected (thumbnail): {candidate[:100]}...")
                except Exception as e:
                    print(f"   Selector {i+1} error: {str(e)[:100]}")
                    # Skip invalid selectors
                    continue
            
            # Select best CSS candidate (prioritize optimized formats)
            if image_candidates:
                print(f"   Found {len(image_candidates)} CSS candidates")
                # Sort by quality: avif > optimized jpg > media domain > others
                def get_priority(candidate):
                    if '.avif' in candidate or '_220x220q75.jpg_.avif' in candidate:
                        return 1
                    elif '_220x220q75' in candidate:
                        return 2
                    elif 'aliexpress-media.com' in candidate:
                        return 3
                    else:
                        return 4
                
                image_candidates.sort(key=lambda x: get_priority(x[1]))
                image_url = image_candidates[0][1]
                print(f"   ✓ SELECTED CSS candidate: {image_url[:150]}...")
            else:
                print(f"   ✗ No valid CSS candidates found")
        else:
            print(f"3. Skipping CSS selectors (already found image)")
        
        # FOURTH PRIORITY: Try script tags (but be careful - might get wrong images)
        if not image_url:
            print(f"4. Checking script tags...")
            scripts = soup.find_all('script')
            script_candidates = []
            print(f"   Found {len(scripts)} script tags")
            
            for i, script in enumerate(scripts):
                if script.string:
                    script_text = script.string
                    
                    # Look for optimized image URLs first (prefer these)
                    # Look for .avif format (best quality)
                    avif_matches = re.findall(r'"(https?://[^"]*\.avif)"', script_text)
                    if avif_matches:
                        print(f"   Script {i+1}: Found {len(avif_matches)} .avif matches")
                    for match in avif_matches:
                        candidate = match.strip().replace('\\/', '/')
                        if candidate.startswith('http') and '50x50' not in candidate and '60x60' not in candidate:
                            script_candidates.append(('avif', candidate))
                            print(f"      ✓ Added avif candidate: {candidate[:150]}...")
                    
                    # Look for optimized .jpg with size parameters
                    optimized_jpg_matches = re.findall(r'"(https?://[^"]*_220x220q75\.jpg[^"]*)"', script_text)
                    if optimized_jpg_matches:
                        print(f"   Script {i+1}: Found {len(optimized_jpg_matches)} optimized jpg matches")
                    for match in optimized_jpg_matches:
                        candidate = match.strip().replace('\\/', '/')
                        if candidate.startswith('http'):
                            script_candidates.append(('optimized_jpg', candidate))
                            print(f"      ✓ Added optimized_jpg candidate: {candidate[:150]}...")
                    
                    # Look for aliexpress-media.com images (better domain)
                    media_matches = re.findall(r'"(https?://[^"]*aliexpress-media\.com[^"]*)"', script_text)
                    if media_matches:
                        print(f"   Script {i+1}: Found {len(media_matches)} aliexpress-media.com matches")
                    for match in media_matches:
                        candidate = match.strip().replace('\\/', '/')
                        if candidate.startswith('http') and any(ext in candidate for ext in ['.jpg', '.jpeg', '.png', '.webp', '.avif']):
                            if '50x50' not in candidate and '60x60' not in candidate:
                                script_candidates.append(('media_domain', candidate))
                                print(f"      ✓ Added media_domain candidate: {candidate[:150]}...")
            
            # Select best script candidate
            if script_candidates:
                print(f"   Found {len(script_candidates)} script candidates")
                def get_script_priority(candidate):
                    if candidate[0] == 'avif':
                        return 1
                    elif candidate[0] == 'optimized_jpg':
                        return 2
                    elif candidate[0] == 'media_domain':
                        return 3
                    else:
                        return 4
                
                script_candidates.sort(key=get_script_priority)
                image_url = script_candidates[0][1]
                print(f"   ✓ SELECTED script candidate: {image_url[:150]}...")
            else:
                print(f"   ✗ No valid script candidates found")
        else:
            print(f"4. Skipping script tags (already found image)")
        
        # LAST RESORT: Generic CSS selectors
        if not image_url:
            print(f"5. Checking generic CSS selectors...")
            generic_selectors = [
                'img[data-pl="product-image"]',
                'img.main-image',
                'img[class*="main-image"]',
                'img[class*="product-image"]',
                'img[itemprop="image"]',
            ]
            for selector in generic_selectors:
                try:
                    img_elems = soup.select(selector)
                    if img_elems:
                        print(f"   Found {len(img_elems)} elements with selector: {selector}")
                        img_elem = img_elems[0]
                        candidate = img_elem.get('src') or img_elem.get('data-src')
                        if candidate:
                            print(f"      Candidate: {candidate[:100]}...")
                            if candidate.startswith('//'):
                                candidate = 'https:' + candidate
                            elif candidate.startswith('/'):
                                candidate = 'https://www.aliexpress.com' + candidate
                            if candidate.startswith('http') and '50x50' not in candidate and '60x60' not in candidate:
                                image_url = candidate
                                print(f"      ✓ SELECTED generic CSS: {image_url[:150]}...")
                                break
                except Exception as e:
                    print(f"   Error with selector {selector}: {str(e)[:100]}")
                    continue
        else:
            print(f"5. Skipping generic CSS selectors (already found image)")
        
        # Product ID was already extracted at the beginning
        # Use the original URL for product_id extraction if not found
        if not product_id:
            id_match = re.search(r'/(\d+)\.html', aliexpress_url)
            if id_match:
                product_id = id_match.group(1)
        
        # Final validation - reject if title is too short or not English
        if title and (len(title) < 5 or (not is_mostly_english(title) and len(title) < 20)):
            # If we have a product ID, use a generic title
            if product_id:
                title = f'Product {product_id}'
            else:
                title = 'Unknown Product'
        
        # Optimize image URL if it's from AliExpress CDN
        if image_url:
            print(f"\n6. Optimizing image URL...")
            print(f"   Original: {image_url[:150]}...")
            # Try to get the best quality version
            if 'alicdn.com' in image_url:
                # If it's a plain .jpg, try to convert to optimized format
                if image_url.endswith('.jpg'):
                    # Try multiple optimized formats
                    base_url = image_url.replace('.jpg', '.jpg_220x220q75.jpg_.avif')
                    # For now, use optimized jpg (avif might not always be available)
                    image_url = base_url
                    print(f"   Converted to optimized jpg: {image_url[:150]}...")
            else:
                print(f"   Not alicdn.com, keeping as-is")
        else:
            print(f"\n✗ NO IMAGE FOUND after all extraction methods!")
        
        # Download and save image locally
        local_image_path = None
        if image_url:
            print(f"\n7. Downloading and saving image locally...")
            local_image_path = download_and_save_image(image_url, product_id)
            if local_image_path:
                print(f"   ✓ Image saved to: {local_image_path}")
            else:
                print(f"   ✗ Failed to save image locally, will use original URL")
        
        print(f"\n=== FINAL RESULT ===")
        print(f"Title: {title or 'Unknown Product'}")
        print(f"Image URL: {image_url or '(empty)'}")
        print(f"Local Image Path: {local_image_path or '(not saved)'}")
        print(f"Product ID: {product_id or '(empty)'}")
        print(f"========================================\n")
        
        return {
            'title': title or 'Unknown Product',
            'image_url': local_image_path or image_url or '',  # Prefer local path
            'product_id': product_id,
            'url': aliexpress_url
        }
    except requests.exceptions.RequestException as e:
        print(f"Network error extracting product info: {e}")
        import traceback
        traceback.print_exc()
        # Try to at least return the product ID if we extracted it
        product_id = None
        id_match = re.search(r'/(\d+)\.html', aliexpress_url)
        if id_match:
            product_id = id_match.group(1)
        return {
            'title': f'Error loading product (Network error)',
            'image_url': '',
            'product_id': product_id,
            'url': aliexpress_url
        }
    except Exception as e:
        print(f"Error extracting product info: {e}")
        import traceback
        traceback.print_exc()
        # Try to at least return the product ID if we extracted it
        product_id = None
        id_match = re.search(r'/(\d+)\.html', aliexpress_url)
        if id_match:
            product_id = id_match.group(1)
        return {
            'title': f'Error loading product: {str(e)[:50]}',
            'image_url': '',
            'product_id': product_id,
            'url': aliexpress_url
        }

@app.route('/api/aliexpress/connect', methods=['POST'])
def connect_aliexpress():
    """Connect to AliExpress - placeholder endpoint"""
    try:
        data = request.json
        cookies = data.get('cookies', '')
        
        if not cookies:
            return jsonify({'error': 'Cookies are required'}), 400
        
        # Placeholder response - fetching logic removed
        return jsonify({
            'success': True,
            'message': 'Fetching logic has been removed. Please implement your own order fetching logic.',
            'orders_added': 0,
            'total_fetched': 0
        })
    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        print(f"Error in connect_aliexpress: {error_trace}")
        return jsonify({
            'success': False,
            'error': str(e),
            'debug': [error_trace]
        }), 500

@app.route('/api/image-proxy')
def image_proxy():
    """Proxy endpoint to fetch images from AliExpress CDN with proper headers to bypass CORS.
    Also saves images locally for future use."""
    image_url = request.args.get('url')
    product_id = request.args.get('product_id')  # Optional product ID for better naming
    
    if not image_url:
        return jsonify({'error': 'URL parameter is required'}), 400
    
    # Try to save image locally first
    local_path = download_and_save_image(image_url, product_id)
    if local_path:
        # If we successfully saved it, redirect to the local path
        return Response('', status=302, headers={'Location': local_path})
    
    # Fallback to proxying if local save failed
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Referer': 'https://www.aliexpress.com/',
        'Accept': 'image/avif,image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.9',
    }
    
    # If the URL is an optimized format that might not exist, try original first
    urls_to_try = [image_url]
    
    # If it's an optimized _220x220q75.jpg that might not exist, try original .jpg
    if '_220x220q75.jpg' in image_url and 'alicdn.com' in image_url:
        original_url = image_url.replace('_220x220q75.jpg', '.jpg')
        urls_to_try.insert(0, original_url)  # Try original first
    
    # Try each URL until one works
    for url_to_try in urls_to_try:
        try:
            response = requests.get(url_to_try, headers=headers, timeout=10, stream=True)
            if response.status_code == 200:
                # Return the image with proper content type and CORS headers
                return Response(
                    response.content,
                    mimetype=response.headers.get('Content-Type', 'image/jpeg'),
                    headers={
                        'Cache-Control': 'public, max-age=86400',
                        'Access-Control-Allow-Origin': '*',
                    }
                )
            elif response.status_code == 404:
                # If 404, try next URL
                continue
            else:
                response.raise_for_status()
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 404:
                # Try next URL
                continue
            else:
                print(f"Error proxying image {url_to_try}: {e}")
        except Exception as e:
            print(f"Error proxying image {url_to_try}: {e}")
            continue
    
    # If all URLs failed, return error
    print(f"Failed to fetch image after trying {len(urls_to_try)} URLs: {image_url}")
    return jsonify({'error': 'Failed to fetch image'}), 500

@app.route('/favicon.ico')
def favicon():
    """Return 204 No Content for favicon requests"""
    return '', 204

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/orders', methods=['GET'])
def get_orders():
    """Get all orders"""
    return jsonify({'orders': orders})

@app.route('/api/orders', methods=['POST'])
def add_order():
    """Add a new order from AliExpress link"""
    data = request.json
    aliexpress_url = data.get('url', '')
    
    if not aliexpress_url:
        return jsonify({'error': 'URL is required'}), 400
    
    # Extract product info
    product_info = extract_product_info(aliexpress_url)
    
    # Create order object
    order = {
        'id': get_next_order_id(),
        'product_title': product_info['title'],
        'product_image': product_info['image_url'],
        'product_url': aliexpress_url,
        'product_id': product_info['product_id'],
        'tracking_number': data.get('tracking_number', ''),
        'status': data.get('status', 'Pending'),
        'added_date': datetime.now().isoformat(),
        'order_date': data.get('order_date', ''),
        'order_id': data.get('order_id', ''),
        'tracking_info': None
    }
    
    # Fetch tracking info if tracking number is provided
    if order['tracking_number']:
        tracking_info = fetch_tracking_info(order['tracking_number'])
        if tracking_info:
            order['tracking_info'] = tracking_info
            # Update status based on tracking if available
            if tracking_info.get('status') and tracking_info['status'] != 'Unknown':
                order['status'] = tracking_info['status']
            # Set order_date from earliest tracking event
            if tracking_info.get('earliest_date'):
                order['order_date'] = tracking_info['earliest_date']
    
    orders.append(order)
    save_orders()
    return jsonify({'order': order, 'message': 'Order added successfully'})

@app.route('/api/orders/<int:order_id>', methods=['PUT'])
def update_order(order_id):
    """Update an existing order"""
    data = request.json
    order = next((o for o in orders if o['id'] == order_id), None)
    
    if not order:
        return jsonify({'error': 'Order not found'}), 404
    
    # Update order fields
    tracking_updated = False
    if 'product_title' in data:
        product_title = data['product_title']
        if product_title and product_title.strip():
            order['product_title'] = product_title.strip()
    
    if 'tracking_number' in data:
        new_tracking = data['tracking_number']
        if new_tracking != order.get('tracking_number', ''):
            order['tracking_number'] = new_tracking
            tracking_updated = True
    
    if 'product_image' in data:
        product_image = data['product_image']
        if product_image and product_image.strip():
            product_image = product_image.strip()
            # If it's a URL (not already a local path), try to save it locally
            if product_image.startswith('http') and not product_image.startswith('/static/images/products/'):
                local_path = download_and_save_image(product_image, order.get('product_id'))
                if local_path:
                    order['product_image'] = local_path
                    print(f"Saved new product image to {local_path}")
                else:
                    order['product_image'] = product_image  # Fallback to original URL
            else:
                order['product_image'] = product_image
    
    # Fetch tracking info if tracking number was updated or if we need to refresh
    if tracking_updated and order['tracking_number']:
        tracking_info = fetch_tracking_info(order['tracking_number'])
        if tracking_info:
            order['tracking_info'] = tracking_info
            # Update status based on tracking if available
            if tracking_info.get('status') and tracking_info['status'] != 'Unknown':
                order['status'] = tracking_info['status']
            # Update order_date from earliest tracking event if not already set
            if tracking_info.get('earliest_date') and not order.get('order_date'):
                order['order_date'] = tracking_info['earliest_date']
    
    save_orders()
    return jsonify({'order': order, 'message': 'Order updated successfully'})

@app.route('/api/orders/<int:order_id>', methods=['DELETE'])
def delete_order(order_id):
    """Delete an order"""
    global orders
    orders = [o for o in orders if o['id'] != order_id]
    save_orders()
    return jsonify({'message': 'Order deleted successfully'})

@app.route('/api/orders/<int:order_id>/tracking', methods=['GET', 'POST'])
def refresh_tracking(order_id):
    """Refresh tracking information for an order"""
    order = next((o for o in orders if o['id'] == order_id), None)
    
    if not order:
        return jsonify({'error': 'Order not found'}), 404
    
    tracking_number = order.get('tracking_number', '')
    if not tracking_number:
        return jsonify({'error': 'No tracking number available'}), 400
    
    tracking_info = fetch_tracking_info(tracking_number)
    if tracking_info:
        order['tracking_info'] = tracking_info
        # Update status based on tracking if available
        if tracking_info.get('status') and tracking_info['status'] != 'Unknown':
            order['status'] = tracking_info['status']
        # Update order_date from earliest tracking event if not already set
        if tracking_info.get('earliest_date') and not order.get('order_date'):
            order['order_date'] = tracking_info['earliest_date']
        save_orders()
        return jsonify({
            'success': True,
            'tracking_info': tracking_info,
            'order': order,
            'message': 'Tracking information updated'
        })
    else:
        return jsonify({
            'success': False,
            'error': 'Failed to fetch tracking information'
        }), 500

@app.route('/api/orders/refresh-all', methods=['POST'])
def refresh_all_tracking():
    """Refresh tracking information for all orders with tracking numbers using bulk API call"""
    try:
        orders_with_tracking = [o for o in orders if o.get('tracking_number') and o.get('tracking_number').strip()]
        
        if not orders_with_tracking:
            return jsonify({
                'success': True,
                'updated': 0,
                'total': 0,
                'message': 'No orders with tracking numbers found'
            })
        
        # Collect all tracking numbers
        tracking_numbers = [o.get('tracking_number', '').strip() for o in orders_with_tracking]
        
        # Make a single bulk API call
        print(f"Fetching tracking info for {len(tracking_numbers)} tracking numbers in bulk...")
        bulk_results = fetch_bulk_tracking_info(tracking_numbers)
        
        updated = 0
        failed = 0
        results = []
        
        # Map tracking numbers to orders and update them
        for order in orders_with_tracking:
            tracking_number = order.get('tracking_number', '').strip()
            if tracking_number:
                if tracking_number in bulk_results:
                    tracking_info = bulk_results[tracking_number]
                    if tracking_info and not tracking_info.get('error'):
                        order['tracking_info'] = tracking_info
                        # Update status based on tracking if available
                        if tracking_info.get('status') and tracking_info['status'] != 'Unknown':
                            order['status'] = tracking_info['status']
                        # Update order_date from earliest tracking event if not already set
                        if tracking_info.get('earliest_date') and not order.get('order_date'):
                            order['order_date'] = tracking_info['earliest_date']
                        updated += 1
                        results.append({
                            'order_id': order['id'],
                            'success': True,
                            'tracking_number': tracking_number
                        })
                    else:
                        failed += 1
                        results.append({
                            'order_id': order['id'],
                            'success': False,
                            'tracking_number': tracking_number,
                            'error': tracking_info.get('error', 'Failed to fetch tracking info') if tracking_info else 'No tracking info returned'
                        })
                else:
                    failed += 1
                    results.append({
                        'order_id': order['id'],
                        'success': False,
                        'tracking_number': tracking_number,
                        'error': 'Tracking number not found in API response'
                    })
        
        save_orders()
        
        print(f"Bulk update completed: {updated} updated, {failed} failed out of {len(orders_with_tracking)} total")
        
        return jsonify({
            'success': True,
            'updated': updated,
            'failed': failed,
            'total': len(orders_with_tracking),
            'results': results,
            'message': f'Updated {updated} out of {len(orders_with_tracking)} orders'
        })
    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        print(f"Error refreshing all tracking: {error_trace}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


if __name__ == '__main__':
    # Load orders from file on startup
    load_orders()
    app.run(debug=True, host='0.0.0.0', port=8000)

