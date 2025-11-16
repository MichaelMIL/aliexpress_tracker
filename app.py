"""Main Flask application"""
from flask import Flask
from models.order import load_orders
from routes import register_routes

app = Flask(__name__)

# Load orders from file on startup (before registering routes)
load_orders()

# Register all routes
register_routes(app)

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=8004)
