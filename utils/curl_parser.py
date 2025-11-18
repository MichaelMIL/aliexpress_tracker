"""cURL command parsing and AliExpress API response extraction utilities"""
import re
import json

def parse_curl_command(curl_command):
    """Parse a cURL command to extract URL, headers, cookies, and POST data"""
    url = None
    headers = {}
    cookies = {}
    post_data = None
    method = 'GET'
    
    # First, remove line continuation backslashes and join lines
    # Replace '\n\' with space, then normalize whitespace
    normalized = curl_command.replace('\\\n', ' ').replace('\\\r\n', ' ')
    # Normalize: remove extra spaces, but preserve quoted strings
    normalized = re.sub(r'\s+', ' ', normalized)
    
    # Check if it's a POST request
    if re.search(r'-X\s+POST', normalized) or re.search(r'--data', normalized):
        method = 'POST'
    
    # Extract URL (first quoted string after 'curl')
    url_match = re.search(r"curl\s+['\"]([^'\"]+)['\"]", normalized)
    if url_match:
        url = url_match.group(1)
    
    # Extract headers (-H 'Header: Value' or -H "Header: Value")
    header_pattern = r"-H\s+['\"]([^:]+):\s*([^'\"]+)['\"]"
    for match in re.finditer(header_pattern, normalized):
        header_name = match.group(1).strip()
        header_value = match.group(2).strip()
        headers[header_name] = header_value
    
    # Extract POST data from --data-raw or --data
    data_raw_match = re.search(r"--data-raw\s+['\"]([^'\"]+)['\"]", normalized)
    if data_raw_match:
        post_data = data_raw_match.group(1)
    else:
        data_match = re.search(r"--data\s+['\"]([^'\"]+)['\"]", normalized)
        if data_match:
            post_data = data_match.group(1)
    
    # Extract cookies from Cookie header
    if 'Cookie' in headers:
        cookie_string = headers['Cookie']
        for cookie_pair in cookie_string.split(';'):
            if '=' in cookie_pair:
                key, value = cookie_pair.split('=', 1)
                cookies[key.strip()] = value.strip()
    
    return url, headers, cookies, method, post_data

def parse_jsonp_response(jsonp_text):
    """Parse JSONP response and extract JSON data"""
    if not jsonp_text or not jsonp_text.strip():
        return None
    
    # Try to remove JSONP wrapper (e.g., mtopjsonp2({...}) or mtopjsonp1({...}))
    # Pattern matches: function_name({...}) or function_name({...});
    jsonp_match = re.search(r'^[^(]+\((.+)\);?\s*$', jsonp_text.strip(), re.DOTALL)
    if jsonp_match:
        json_text = jsonp_match.group(1).strip()
    else:
        # If no JSONP wrapper found, try to use the text as-is
        json_text = jsonp_text.strip()
    
    # Try to parse as JSON
    try:
        return json.loads(json_text)
    except json.JSONDecodeError as e:
        # If parsing fails, try to find JSON object in the text
        # Look for {...} pattern
        json_obj_match = re.search(r'\{.*\}', json_text, re.DOTALL)
        if json_obj_match:
            try:
                return json.loads(json_obj_match.group(0))
            except json.JSONDecodeError:
                pass
        
        print(f"JSON decode error: {e}")
        print(f"Attempted to parse (first 500 chars): {json_text[:500]}")
        return None

def extract_orders_from_api_response(api_data):
    """Extract order information from AliExpress API response.
    Groups multiple orderLines into a single order with sub_items."""
    orders_dict = {}  # Key: order_id, Value: order data with sub_items
    
    try:
        # Navigate to data.data where orders are stored
        data_section = api_data.get('data', {}).get('data', {})
        
        # Find all order entries (keys starting with 'pc_om_list_order_')
        for key, order_data in data_section.items():
            if key.startswith('pc_om_list_order_') and isinstance(order_data, dict):
                fields = order_data.get('fields', {})
                order_id = fields.get('orderId', '')
                order_date_text = fields.get('orderDateText', '')
                
                # Extract order lines (products in the order)
                order_lines = fields.get('orderLines', [])
                
                if not order_id:
                    continue
                
                for line in order_lines:
                    product_id = line.get('productId', '')
                    item_title = line.get('itemTitle', '')
                    item_detail_url = line.get('itemDetailUrl', '')
                    item_img_url = line.get('itemImgUrl', '')
                    item_price_text = line.get('itemPriceText', '')
                    
                    # Build full URL if it's relative
                    if item_detail_url and item_detail_url.startswith('//'):
                        item_detail_url = 'https:' + item_detail_url
                    elif item_detail_url and not item_detail_url.startswith('http'):
                        item_detail_url = 'https://www.aliexpress.com' + item_detail_url
                    
                    if product_id and item_title:
                        # Initialize order if not exists
                        if order_id not in orders_dict:
                            orders_dict[order_id] = {
                                'order_id': order_id,
                                'order_date': order_date_text,
                                'total_price': fields.get('totalPriceText', ''),
                                'sub_items': []
                            }
                        
                        orders_dict[order_id]['sub_items'].append({
                            'product_id': product_id,
                            'product_title': item_title,
                            'product_url': item_detail_url or f'https://www.aliexpress.com/item/{product_id}.html',
                            'product_image': item_img_url,
                            'price': item_price_text
                        })
        
        # Remove orders with no sub_items
        orders_dict = {k: v for k, v in orders_dict.items() if v.get('sub_items')}
    except Exception as e:
        print(f"Error extracting orders: {e}")
        import traceback
        traceback.print_exc()
    
    # Convert dict to list
    return list(orders_dict.values())

