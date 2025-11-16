"""Image handling utilities"""
import requests
import os
import hashlib
from urllib.parse import urlparse
from config import IMAGES_DIR

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

