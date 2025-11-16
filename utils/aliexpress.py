"""AliExpress product information extraction utilities"""
import requests
from bs4 import BeautifulSoup
import re
import json
from .images import download_and_save_image

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

# Note: extract_product_info is very large (~600 lines)
# It will be added in the next step due to size constraints

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
