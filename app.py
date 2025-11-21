"""Main Flask application"""
from flask import Flask
from models.order import load_orders
from routes import register_routes
from utils.scheduler import start_scheduler

app = Flask(__name__)

# Load orders from file on startup (before registering routes)
load_orders()

# Register all routes
register_routes(app)

# Start auto-update scheduler
start_scheduler()

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=8004)
