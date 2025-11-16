# AliExpress Order Tracker

A Python web application for tracking AliExpress orders with automatic tracking updates, bulk import, and a beautiful, modern interface.

## Features

- 📦 **Product Information Extraction**: Automatically extracts product title and image from AliExpress URLs
- 🖼️ **Local Image Storage**: Downloads and stores product images locally for offline access
- 📊 **Order Tracking**: Automatic tracking updates via Cainiao API with bulk refresh support
- 🔄 **Bulk Operations**: Update all orders' tracking information with a single click
- 📥 **Import from AliExpress**: Import orders directly from AliExpress using cURL commands
- 📦 **Multi-Item Orders**: View and manage orders with multiple items (sub-items)
- 💰 **Price Tracking**: Display and sort orders by price
- 🔍 **Filtering & Sorting**: Filter by status, search by product name, sort by various criteria
- 📤 **Export**: Export orders to CSV format
- 🎨 **Modern UI**: Beautiful gradient design with smooth animations and responsive layout
- 📱 **Responsive Design**: Works on desktop and mobile devices

## Project Structure

```
aliexpress_tracker/
├── app.py                    # Main Flask application
├── config.py                 # Configuration constants
├── models/
│   ├── __init__.py
│   └── order.py             # Order data model and storage
├── utils/
│   ├── __init__.py
│   ├── images.py            # Image download and storage
│   ├── tracking.py          # Tracking information fetching
│   ├── aliexpress.py        # AliExpress product extraction
│   └── curl_parser.py       # cURL parsing and order extraction
├── routes/
│   ├── __init__.py          # Route registration
│   ├── main.py              # Main page routes
│   ├── api.py               # API routes (orders, tracking)
│   └── import_routes.py     # Import routes
├── static/
│   ├── css/
│   │   └── style.css        # Styles
│   ├── js/
│   │   └── main.js          # Client-side JavaScript
│   └── images/
│       └── products/        # Locally stored product images
├── templates/
│   ├── index.html           # Main application page
│   └── import.html          # Import page (legacy)
└── orders.json              # Order data storage (gitignored)
```

## Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd aliexpress_tracker
```

2. Install Python dependencies:
```bash
pip install -r requirements.txt
```

3. Create the images directory (if it doesn't exist):
```bash
mkdir -p static/images/products
```

## Usage

1. Start the Flask server:
```bash
python app.py
```

2. Open your browser and navigate to:
```
http://localhost:8000
```

### Adding Orders

**Method 1: From AliExpress URL**
- Click the floating action button (FAB) to open the "Add Order" modal
- Paste an AliExpress product URL
- Optionally add a tracking number
- Click "Add Order" to extract product info and add it to your tracker

**Method 2: Import from AliExpress**
- Click "Import Orders from AliExpress" in the Bulk Actions section
- Follow the instructions to copy a cURL command from your browser's Network tab
- Paste the cURL command and click "Import Orders"
- Orders with multiple items will be grouped automatically

### Managing Orders

- **Edit Orders**: Click "Edit" to modify product title, image URL, or tracking number
- **Delete Orders**: Click "Delete" to remove an order
- **View Sub-Items**: Click the "📦 X items" button to view all items in multi-item orders
- **Refresh Tracking**: Click "🔄" to update tracking information for a single order
- **Bulk Update**: Click "Update All Parcels" to refresh tracking for all orders (skips delivered orders)
- **View Events**: Click "📦" to view detailed tracking events timeline

### Filtering and Sorting

- **Filter by Status**: Use the status dropdown to filter orders
- **Search**: Type in the search box to filter by product name
- **Sort**: Choose from various sorting options (date, price, tracking number, etc.)
- **Hide Delivered**: Check the "Hide Delivered" checkbox to hide completed orders
- **Export**: Click "Export Orders" to download filtered orders as CSV

## API Endpoints

### Orders
- `GET /api/orders` - Get all orders
- `POST /api/orders` - Add a new order from URL
- `PUT /api/orders/<id>` - Update an order
- `DELETE /api/orders/<id>` - Delete an order

### Tracking
- `GET /api/orders/<id>/tracking` - Get tracking information for an order
- `POST /api/orders/<id>/tracking` - Refresh tracking information for an order
- `POST /api/orders/refresh-all` - Refresh tracking for all orders (bulk)

### Import
- `POST /api/import/orders` - Import orders from AliExpress API (cURL command)

### Utilities
- `GET /api/image-proxy` - Proxy endpoint for AliExpress images (with local caching)
- `GET /favicon.ico` - Favicon endpoint

## Data Storage

- Orders are stored in `orders.json` (gitignored)
- Product images are stored in `static/images/products/` (gitignored)
- All data persists between application restarts

## Configuration

Configuration is managed in `config.py`:
- `ORDERS_FILE`: Path to the orders JSON file (default: `orders.json`)
- `IMAGES_DIR`: Directory for storing product images (default: `static/images/products`)

## Features in Detail

### Tracking Integration
- Automatically fetches tracking information from Cainiao API
- Supports bulk tracking updates for multiple orders
- Skips already delivered orders during bulk updates
- Displays tracking status, carrier, and latest update information
- Shows detailed tracking events timeline

### Image Management
- Downloads product images from AliExpress CDN
- Stores images locally for offline access and faster loading
- Handles CORS issues by proxying images through the application
- Supports multiple image formats (JPG, PNG, WebP, AVIF)

### Multi-Item Orders
- Groups multiple items from the same AliExpress order
- Displays combined title (e.g., "Product Name (+2 more)")
- Shows all sub-items in a modal with images, prices, and links
- Stores individual item information for each sub-item

## Development

The application uses a modular structure:
- **Models**: Data models and storage functions
- **Utils**: Utility functions for external API calls and data processing
- **Routes**: Flask blueprints organized by feature

## Notes

- Orders are stored in JSON format. For production use with large datasets, consider implementing a database (SQLite, PostgreSQL, etc.)
- Product information extraction uses web scraping, which may need adjustments if AliExpress changes their HTML structure
- Tracking information is fetched from the public Cainiao API
- Import functionality requires copying a cURL command from your browser's developer tools (includes authentication cookies)

## Future Enhancements

- Database integration for better performance and scalability
- Real-time tracking updates with webhooks
- Email notifications for order status changes
- Multiple user support with authentication
- Order statistics and analytics
- Dark mode support
