"""Import routes for AliExpress order import"""
from flask import Blueprint, request, jsonify
import requests
from datetime import datetime
from models.order import orders, save_orders, get_next_order_id
from utils.images import download_and_save_image
from utils.curl_parser import parse_curl_command, parse_jsonp_response, extract_orders_from_api_response
from utils.url_creator import fetch_tracking_number_from_order

import_bp = Blueprint('import', __name__)

@import_bp.route('/orders', methods=['POST'])
def import_orders():
    """Import orders from AliExpress API using a cURL command"""
    try:
        data = request.json
        curl_command = data.get('curl_command', '')
        
        if not curl_command:
            return jsonify({'success': False, 'error': 'cURL command is required'}), 400
        
        # Parse cURL command
        url, headers, cookies, method, post_data = parse_curl_command(curl_command)
        
        if not url:
            return jsonify({'success': False, 'error': 'Could not extract URL from cURL command'}), 400
        
        # Make the API request
        print(f"Fetching orders from: {url[:100]}... (method: {method})")
        if method == 'POST' and post_data:
            response = requests.post(url, headers=headers, cookies=cookies, data=post_data, timeout=30)
        else:
            response = requests.get(url, headers=headers, cookies=cookies, timeout=30)
        
        if response.status_code != 200:
            error_text = response.text[:500] if response.text else 'No response body'
            print(f"API request failed: Status {response.status_code}, Response: {error_text}")
            return jsonify({
                'success': False,
                'error': f'API request failed with status {response.status_code}. Response may not be valid JSON.'
            }), 400
        
        # Debug: print first 500 chars of response
        response_preview = response.text[:500] if response.text else ''
        print(f"Response preview: {response_preview}")
        
        # Parse response (could be JSONP or JSON)
        api_data = parse_jsonp_response(response.text)
        
        # If JSONP parsing failed, try direct JSON parsing
        if not api_data:
            import json
            try:
                api_data = json.loads(response.text)
            except json.JSONDecodeError as e:
                print(f"JSON parsing error: {e}")
                print(f"Response text (first 1000 chars): {response.text[:1000]}")
                return jsonify({
                    'success': False,
                    'error': f'Failed to parse API response. The response may not be valid JSON/JSONP. Error: {str(e)}'
                }), 400
        
        if not api_data:
            return jsonify({
                'success': False,
                'error': 'Failed to parse API response'
            }), 400
        
        # Check for API errors
        ret = api_data.get('ret', [])
        if ret and not any('SUCCESS' in r for r in ret):
            return jsonify({
                'success': False,
                'error': f'API returned error: {ret}'
            }), 400
        
        # Extract orders from response
        extracted_orders = extract_orders_from_api_response(api_data)
        
        if not extracted_orders:
            return jsonify({
                'success': True,
                'imported': 0,
                'message': 'No orders found in the response'
            })
        
        # Extract cookie string from headers for tracking number fetching
        # Try to get from Cookie header first, otherwise reconstruct from cookies dict
        cookie_string = headers.get('Cookie', '')
        if not cookie_string and cookies:
            # Reconstruct cookie string from cookies dict
            cookie_pairs = [f"{key}={value}" for key, value in cookies.items()]
            cookie_string = '; '.join(cookie_pairs)
        
        # Create orders in the system
        imported_count = 0
        skipped_count = 0
        created_orders = []
        tracking_fetched_count = 0
        
        for order_data in extracted_orders:
            order_id = order_data.get('order_id', '')
            sub_items = order_data.get('sub_items', [])
            
            if not order_id or not sub_items:
                continue
            
            # Check if order already exists (by order_id)
            existing_order = next(
                (o for o in orders 
                 if o.get('order_id') == order_id),
                None
            )
            
            if existing_order:
                skipped_count += 1
                continue
            
            # Use first sub-item as main order display (or combine titles if multiple)
            first_item = sub_items[0]
            if len(sub_items) > 1:
                product_title = f"{first_item['product_title']} (+{len(sub_items) - 1} more)"
            else:
                product_title = first_item['product_title']
            
            # Download and save image for first item
            local_image_path = None
            if first_item.get('product_image'):
                local_image_path = download_and_save_image(
                    first_item['product_image'],
                    first_item['product_id']
                )
            
            # Download and save images for all sub-items
            processed_sub_items = []
            for sub_item in sub_items:
                sub_image_path = None
                if sub_item.get('product_image'):
                    sub_image_path = download_and_save_image(
                        sub_item['product_image'],
                        sub_item['product_id']
                    )
                
                processed_sub_items.append({
                    'product_id': sub_item['product_id'],
                    'product_title': sub_item['product_title'],
                    'product_url': sub_item['product_url'],
                    'product_image': sub_image_path or sub_item.get('product_image', ''),
                    'price': sub_item.get('price', '')
                })
            
            # Fetch tracking number using url_creator
            tracking_number = ''
            if cookie_string and order_id:
                print(f"Fetching tracking number for order {order_id}...")
                try:
                    tracking_number = fetch_tracking_number_from_order(cookie_string, order_id)
                    if tracking_number:
                        print(f"Found tracking number: {tracking_number} for order {order_id}")
                        tracking_fetched_count += 1
                    else:
                        print(f"No tracking number found for order {order_id}")
                except Exception as e:
                    print(f"Error fetching tracking number for order {order_id}: {e}")
            
            # Create order object with sub_items
            order = {
                'id': get_next_order_id(),
                'product_title': product_title,
                'product_image': local_image_path or first_item.get('product_image', ''),
                'product_url': first_item['product_url'],
                'product_id': first_item['product_id'],
                'tracking_number': tracking_number,
                'status': 'Pending',
                'added_date': datetime.now().isoformat(),
                'order_date': order_data.get('order_date', ''),
                'order_id': order_id,
                'tracking_info': None,
                'price': order_data.get('total_price', ''),
                'sub_items': processed_sub_items
            }
            
            orders.append(order)
            created_orders.append({
                'product_title': order['product_title'],
                'product_id': order['product_id'],
                'order_date': order.get('order_date', ''),
                'price': order.get('price', ''),
                'sub_items_count': len(processed_sub_items),
                'tracking_number': tracking_number if tracking_number else None
            })
            imported_count += 1
        
        # Save orders to file
        if imported_count > 0:
            save_orders()
        
        return jsonify({
            'success': True,
            'imported': imported_count,
            'skipped': skipped_count,
            'total_found': len(extracted_orders),
            'tracking_fetched': tracking_fetched_count,
            'orders': created_orders
        })
        
    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        print(f"Error importing orders: {error_trace}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

