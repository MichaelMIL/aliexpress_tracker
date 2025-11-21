"""API routes for orders and tracking"""
from flask import Blueprint, request, jsonify, Response
from datetime import datetime
from models.order import orders, save_orders, get_next_order_id
from utils.images import download_and_save_image
from utils.tracking import fetch_tracking_info, fetch_bulk_tracking_info
from utils.aliexpress import extract_product_info
from utils.doar_israel import fetch_doar_tracking_info
from config import (
    get_doar_api_key,
    set_doar_api_key,
    get_cainiao_last_update,
    set_cainiao_last_update,
    get_doar_last_update,
    set_doar_last_update
)

api_bp = Blueprint('api', __name__)

@api_bp.route('/orders', methods=['GET'])
def get_orders():
    """Get all orders"""
    return jsonify({'orders': orders})

@api_bp.route('/orders', methods=['POST'])
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
            if tracking_info.get('status') and tracking_info['status'] != 'Unknown':
                order['status'] = tracking_info['status']
            if tracking_info.get('earliest_date'):
                order['order_date'] = tracking_info['earliest_date']
    
    orders.append(order)
    save_orders()
    return jsonify({'order': order, 'message': 'Order added successfully'})

@api_bp.route('/orders/<int:order_id>', methods=['PUT'])
def update_order(order_id):
    """Update an existing order"""
    data = request.json
    order = next((o for o in orders if o['id'] == order_id), None)
    
    if not order:
        return jsonify({'error': 'Order not found'}), 404
    
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
            if product_image.startswith('http') and not product_image.startswith('/static/images/products/'):
                local_path = download_and_save_image(product_image, order.get('product_id'))
                if local_path:
                    order['product_image'] = local_path
                    print(f"Saved new product image to {local_path}")
                else:
                    order['product_image'] = product_image
            else:
                order['product_image'] = product_image
    
    if tracking_updated and order['tracking_number']:
        tracking_info = fetch_tracking_info(order['tracking_number'])
        if tracking_info:
            order['tracking_info'] = tracking_info
            if tracking_info.get('status') and tracking_info['status'] != 'Unknown':
                order['status'] = tracking_info['status']
            if tracking_info.get('earliest_date') and not order.get('order_date'):
                order['order_date'] = tracking_info['earliest_date']
    
    save_orders()
    return jsonify({'order': order, 'message': 'Order updated successfully'})

@api_bp.route('/orders/<int:order_id>', methods=['DELETE'])
def delete_order(order_id):
    """Delete an order"""
    from models.order import orders
    orders[:] = [o for o in orders if o['id'] != order_id]
    save_orders()
    return jsonify({'message': 'Order deleted successfully'})

@api_bp.route('/orders/<int:order_id>/tracking', methods=['GET', 'POST'])
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
        if tracking_info.get('status') and tracking_info['status'] != 'Unknown':
            order['status'] = tracking_info['status']
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

@api_bp.route('/orders/refresh-all', methods=['POST'])
def refresh_all_tracking():
    """Refresh tracking information for all orders with tracking numbers using bulk API call.
    Skips orders that are already in 'delivered' status."""
    try:
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
        
        if not orders_with_tracking:
            return jsonify({
                'success': True,
                'updated': 0,
                'total': 0,
                'skipped': skipped_delivered,
                'message': f'No orders to update. {skipped_delivered} delivered orders skipped.' if skipped_delivered > 0 else 'No orders with tracking numbers found'
            })
        
        tracking_numbers = [o.get('tracking_number', '').strip() for o in orders_with_tracking]
        
        print(f"Fetching tracking info for {len(tracking_numbers)} tracking numbers in bulk...")
        bulk_results = fetch_bulk_tracking_info(tracking_numbers)
        
        updated = 0
        failed = 0
        results = []
        
        for order in orders_with_tracking:
            tracking_number = order.get('tracking_number', '').strip()
            if tracking_number:
                if tracking_number in bulk_results:
                    tracking_info = bulk_results[tracking_number]
                    if tracking_info and not tracking_info.get('error'):
                        order['tracking_info'] = tracking_info
                        if tracking_info.get('status') and tracking_info['status'] != 'Unknown':
                            order['status'] = tracking_info['status']
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
        
        # Update last update time for Cainiao
        set_cainiao_last_update()
        
        print(f"Bulk update completed: {updated} updated, {failed} failed out of {len(orders_with_tracking)} total, {skipped_delivered} delivered orders skipped")
        
        message = f'Updated {updated} out of {len(orders_with_tracking)} orders'
        if skipped_delivered > 0:
            message += f' ({skipped_delivered} delivered orders skipped)'
        
        return jsonify({
            'success': True,
            'updated': updated,
            'failed': failed,
            'total': len(orders_with_tracking),
            'skipped': skipped_delivered,
            'results': results,
            'message': message
        })
    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        print(f"Error refreshing all tracking: {error_trace}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@api_bp.route('/aliexpress/connect', methods=['POST'])
def connect_aliexpress():
    """Connect to AliExpress - placeholder endpoint"""
    try:
        data = request.json
        cookies = data.get('cookies', '')
        
        if not cookies:
            return jsonify({'error': 'Cookies are required'}), 400
        
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

@api_bp.route('/image-proxy')
def image_proxy():
    """Proxy endpoint to fetch images from AliExpress CDN with proper headers to bypass CORS.
    Also saves images locally for future use."""
    import requests
    image_url = request.args.get('url')
    product_id = request.args.get('product_id')
    
    if not image_url:
        return jsonify({'error': 'URL parameter is required'}), 400
    
    local_path = download_and_save_image(image_url, product_id)
    if local_path:
        return Response('', status=302, headers={'Location': local_path})
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Referer': 'https://www.aliexpress.com/',
        'Accept': 'image/avif,image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.9',
    }
    
    urls_to_try = [image_url]
    if '_220x220q75.jpg' in image_url and 'alicdn.com' in image_url:
        original_url = image_url.replace('_220x220q75.jpg', '.jpg')
        urls_to_try.insert(0, original_url)
    
    for url_to_try in urls_to_try:
        try:
            response = requests.get(url_to_try, headers=headers, timeout=10, stream=True)
            if response.status_code == 200:
                return Response(
                    response.content,
                    mimetype=response.headers.get('Content-Type', 'image/jpeg'),
                    headers={
                        'Cache-Control': 'public, max-age=86400',
                        'Access-Control-Allow-Origin': '*',
                    }
                )
            elif response.status_code == 404:
                continue
            else:
                response.raise_for_status()
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 404:
                continue
            else:
                print(f"Error proxying image {url_to_try}: {e}")
        except Exception as e:
            print(f"Error proxying image {url_to_try}: {e}")
            continue
    
    print(f"Failed to fetch image after trying {len(urls_to_try)} URLs: {image_url}")
    return jsonify({'error': 'Failed to fetch image'}), 500

@api_bp.route('/favicon.ico')
def favicon():
    """Return 204 No Content for favicon requests"""
    return '', 204

@api_bp.route('/config/doar-api-key', methods=['GET', 'POST'])
def doar_api_key():
    """Get or set Doar Israel API key"""
    if request.method == 'GET':
        api_key = get_doar_api_key()
        # Return masked key for security (only show last 4 characters)
        masked_key = '*' * (len(api_key) - 4) + api_key[-4:] if len(api_key) > 4 else '*' * len(api_key)
        return jsonify({
            'api_key_set': bool(api_key),
            'masked_key': masked_key if api_key else ''
        })
    else:  # POST
        data = request.json
        api_key = data.get('api_key', '').strip()
        
        if not api_key:
            return jsonify({'error': 'API key is required'}), 400
        
        set_doar_api_key(api_key)
        return jsonify({
            'success': True,
            'message': 'API key saved successfully'
        })

@api_bp.route('/orders/<int:order_id>/doar-tracking', methods=['GET', 'POST'])
def refresh_doar_tracking(order_id):
    """Refresh Doar Israel tracking information for an order"""
    order = next((o for o in orders if o['id'] == order_id), None)
    
    if not order:
        return jsonify({'error': 'Order not found'}), 404
    
    tracking_number = order.get('tracking_number', '')
    if not tracking_number:
        return jsonify({'error': 'No tracking number available'}), 400
    
    tracking_info = fetch_doar_tracking_info(tracking_number)
    if tracking_info:
        # Store Doar Israel tracking info separately
        if 'doar_tracking_info' not in order:
            order['doar_tracking_info'] = {}
        order['doar_tracking_info'] = tracking_info
        save_orders()
        return jsonify({
            'success': True,
            'tracking_info': tracking_info,
            'order': order,
            'message': 'Doar Israel tracking information updated'
        })
    else:
        return jsonify({
            'success': False,
            'error': 'Failed to fetch Doar Israel tracking information'
        }), 500

@api_bp.route('/orders/refresh-all-doar', methods=['POST'])
def refresh_all_doar_tracking():
    """Refresh Doar Israel tracking information for all orders with tracking numbers"""
    try:
        api_key = get_doar_api_key()
        if not api_key:
            return jsonify({
                'success': False,
                'error': 'Doar Israel API key not configured. Please set it in the bulk actions.'
            }), 400
        
        orders_with_tracking = []
        
        for o in orders:
            if o.get('tracking_number') and o.get('tracking_number').strip():
                orders_with_tracking.append(o)
        
        if not orders_with_tracking:
            return jsonify({
                'success': True,
                'updated': 0,
                'total': 0,
                'message': 'No orders with tracking numbers found'
            })
        
        updated = 0
        failed = 0
        results = []
        
        for order in orders_with_tracking:
            tracking_number = order.get('tracking_number', '').strip()
            if tracking_number:
                tracking_info = fetch_doar_tracking_info(tracking_number)
                if tracking_info and not tracking_info.get('error'):
                    if 'doar_tracking_info' not in order:
                        order['doar_tracking_info'] = {}
                    order['doar_tracking_info'] = tracking_info
                    updated += 1
                    results.append({
                        'order_id': order['id'],
                        'success': True,
                        'tracking_number': tracking_number
                    })
                else:
                    failed += 1
                    error_msg = tracking_info.get('error', 'Failed to fetch tracking info') if tracking_info else 'No tracking info returned'
                    results.append({
                        'order_id': order['id'],
                        'success': False,
                        'tracking_number': tracking_number,
                        'error': error_msg
                    })
        
        save_orders()
        
        # Update last update time for Doar Israel
        set_doar_last_update()
        
        print(f"Doar Israel bulk update completed: {updated} updated, {failed} failed out of {len(orders_with_tracking)} total")
        
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
        print(f"Error refreshing all Doar Israel tracking: {error_trace}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@api_bp.route('/auto-update/last-updates', methods=['GET'])
def get_last_updates():
    """Get the last update times for Cainiao and Doar Israel"""
    try:
        cainiao_last = get_cainiao_last_update()
        doar_last = get_doar_last_update()
        
        return jsonify({
            'success': True,
            'cainiao_last_update': cainiao_last.isoformat() if cainiao_last else None,
            'doar_last_update': doar_last.isoformat() if doar_last else None
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

