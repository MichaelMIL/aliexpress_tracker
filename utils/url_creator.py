import re
import time
import hashlib
import urllib.parse
import json
import requests


def extract_token_from_cookie(cookie_header: str) -> str:
    # _m_h5_tk=token_timestamp
    m = re.search(r"(?:^|;\s*)_m_h5_tk=([^;]+)", cookie_header)
    if not m:
        raise ValueError("_m_h5_tk not found in Cookie header")
    full = m.group(1)
    token = full.split("_", 1)[0]
    return token


def build_url_from_cookie_and_order_id(cookie: str, order_id: str) -> str:
    """
    Build a signed URL for AliExpress order tracking API.
    
    Args:
        cookie: Cookie string containing _m_h5_tk token
        order_id: Trade order ID to query
    
    Returns:
        Signed URL with current timestamp and valid signature
    """
    # Extract token from cookie
    token = extract_token_from_cookie(cookie)
    
    # Build data JSON
    data_dict = {
        "tradeOrderId": order_id,
        "tradeOrderLineId": "",
        "terminalType": "PC",
        "needPageDisplayInfo": True,
        "timeZone": "GMT+02:00",
        "__inline": "true",
        "_lang": "en_IL",
        "_currency": "USD"
    }
    data_json = json.dumps(data_dict, separators=(',', ':'))
    
    # API configuration
    app_key = "12574478"
    base_url = "https://acs.aliexpress.com/h5/mtop.ae.ld.querydetail/1.0/"
    
    # New timestamp in ms
    t_ms = int(time.time() * 1000)
    t_str = str(t_ms)
    
    # Compute sign: md5(token + '&' + t + '&' + appKey + '&' + data_json)
    sign_src = f"{token}&{t_str}&{app_key}&{data_json}"
    sign = hashlib.md5(sign_src.encode("utf-8")).hexdigest()
    
    # Build query parameters
    query_params = [
        ("jsv", "2.5.1"),
        ("appKey", app_key),
        ("t", t_str),
        ("sign", sign),
        ("api", "mtop.ae.ld.querydetail"),
        ("type", "originaljsonp"),
        ("v", "1.0"),
        ("timeout", "15000"),
        ("dataType", "originaljsonp"),
        ("callback", "mtopjsonp1"),
        ("data", data_json),
    ]
    
    # Encode query
    query = urllib.parse.urlencode(query_params, quote_via=urllib.parse.quote)
    
    # Build final URL
    url = f"{base_url}?{query}"
    
    return url


def fetch_tracking_number_from_order(cookie: str, order_id: str) -> str:
    """
    Fetch tracking number (mailNo) for an AliExpress order.
    
    Args:
        cookie: Cookie string containing _m_h5_tk token
        order_id: Trade order ID to query
    
    Returns:
        Tracking number (mailNo) if found, empty string otherwise
    """
    try:
        # Build the signed URL
        url = build_url_from_cookie_and_order_id(cookie, order_id)
        
        # Prepare headers (similar to browser request)
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:144.0) Gecko/20100101 Firefox/144.0',
            'Accept': '*/*',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate, br, zstd',
            'Referer': f'https://www.aliexpress.com/p/tracking/index.html?_addShare=no&_login=yes&tradeOrderId={order_id}',
            'Sec-Fetch-Dest': 'script',
            'Sec-Fetch-Mode': 'no-cors',
            'Sec-Fetch-Site': 'same-site',
            'Connection': 'keep-alive',
        }
        
        # Parse cookies from cookie string
        cookies_dict = {}
        for cookie_pair in cookie.split(';'):
            if '=' in cookie_pair:
                key, value = cookie_pair.split('=', 1)
                cookies_dict[key.strip()] = value.strip()
        
        # Make the API request
        response = requests.get(url, headers=headers, cookies=cookies_dict, timeout=30)
        
        if response.status_code != 200:
            print(f"Failed to fetch order details: {response.status_code}")
            return ""
        
        # Parse JSONP response
        response_text = response.text
        jsonp_match = re.search(r'^[^(]+\((.+)\);?\s*$', response_text, re.DOTALL)
        if jsonp_match:
            json_text = jsonp_match.group(1)
        else:
            json_text = response_text
        
        try:
            api_data = json.loads(json_text)
        except json.JSONDecodeError:
            print(f"Failed to parse JSON response")
            return ""
        
        # Check for API errors
        ret = api_data.get('ret', [])
        if ret and not any('SUCCESS' in r for r in ret):
            print(f"API returned error: {ret}")
            return ""
        
        # Navigate to data section and find mailNo
        # The structure is typically: data.data.logisticsInfoList[0].mailNo
        data_section = api_data.get('data', {})
        
        # Try different possible paths for mailNo
        mail_no = None
        
        # Path 1: data.data.logisticsInfoList[0].mailNo
        logistics_info_list = data_section.get('data', {}).get('logisticsInfoList', [])
        if logistics_info_list and len(logistics_info_list) > 0:
            mail_no = logistics_info_list[0].get('mailNo')
        
        # Path 2: data.logisticsInfoList[0].mailNo
        if not mail_no:
            logistics_info_list = data_section.get('logisticsInfoList', [])
            if logistics_info_list and len(logistics_info_list) > 0:
                mail_no = logistics_info_list[0].get('mailNo')
        
        # Path 3: data.data.mailNo (direct)
        if not mail_no:
            mail_no = data_section.get('data', {}).get('mailNo')
        
        # Path 4: data.mailNo (direct)
        if not mail_no:
            mail_no = data_section.get('mailNo')
        
        # Path 5: Search recursively in the data structure
        if not mail_no:
            def find_mail_no(obj, depth=0):
                if depth > 10:  # Prevent infinite recursion
                    return None
                if isinstance(obj, dict):
                    if 'mailNo' in obj:
                        return obj['mailNo']
                    for value in obj.values():
                        result = find_mail_no(value, depth + 1)
                        if result:
                            return result
                elif isinstance(obj, list):
                    for item in obj:
                        result = find_mail_no(item, depth + 1)
                        if result:
                            return result
                return None
            
            mail_no = find_mail_no(data_section)
        
        if mail_no:
            return str(mail_no).strip()
        
        return ""
        
    except Exception as e:
        print(f"Error fetching tracking number for order {order_id}: {e}")
        import traceback
        traceback.print_exc()
        return ""


def main():
    # Example usage - replace with your actual cookie and order_id
    cookie = "FILL_IN"
    order_id = "FILL"
    
    url = build_url_from_cookie_and_order_id(cookie, order_id)
    
    print("=== Generated URL ===")
    print(url)


if __name__ == "__main__":
    main()
