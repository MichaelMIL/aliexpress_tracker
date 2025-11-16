# AliExpress Order Tracker

A Python web application for tracking AliExpress orders with a beautiful, modern interface.

## Features

- 📦 **Product Information Extraction**: Automatically extracts product title and image from AliExpress URLs
- 🖼️ **Product Images**: Displays product images in the order table
- 🔐 **JWT Token Authentication**: Connect to AliExpress using JWT tokens
- 📊 **Table View**: Clean, responsive table view for all orders
- ✏️ **Order Management**: Add, edit, and delete orders
- 📍 **Tracking Numbers**: Store and display tracking numbers for each order
- 🎨 **Modern UI**: Beautiful gradient design with smooth animations

## Installation

1. Install Python dependencies:
```bash
pip install -r requirements.txt
```

## Usage

1. Start the Flask server:
```bash
python app.py
```

2. Open your browser and navigate to:
```
http://localhost:5000
```

3. **Add Orders**:
   - Paste an AliExpress product URL in the "Add Order from Link" section
   - Optionally add a tracking number
   - Click "Add Order" to extract product info and add it to your tracker

4. **Connect to AliExpress**:
   - Paste your JWT token in the "Connect to AliExpress" section
   - Click "Fetch All Orders" to retrieve all your orders from AliExpress

5. **Manage Orders**:
   - Edit orders by clicking the "Edit" button
   - Delete orders by clicking the "Delete" button
   - Update tracking numbers and order status

## API Endpoints

- `GET /api/orders` - Get all orders
- `POST /api/orders` - Add a new order from URL
- `PUT /api/orders/<id>` - Update an order
- `DELETE /api/orders/<id>` - Delete an order
- `POST /api/aliexpress/connect` - Connect to AliExpress and fetch orders

## Notes

- The AliExpress API integration is currently a placeholder. You'll need to update the `fetch_orders_from_aliexpress()` function in `app.py` with the actual AliExpress API endpoint and authentication method.
- Orders are stored in memory. For production use, consider implementing a database (SQLite, PostgreSQL, etc.).
- Product information extraction uses web scraping, which may need adjustments if AliExpress changes their HTML structure.

## Future Enhancements

- Database integration for persistent storage
- Real-time tracking updates
- Email notifications for order status changes
- Export orders to CSV/Excel
- Multiple user support with authentication

