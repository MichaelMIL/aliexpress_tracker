"""Routes package - registers all blueprints"""
from flask import Blueprint
from .main import main_bp
from .api import api_bp
from .import_routes import import_bp

def register_routes(app):
    """Register all blueprints with the Flask app"""
    app.register_blueprint(main_bp)
    app.register_blueprint(api_bp, url_prefix='/api')
    app.register_blueprint(import_bp, url_prefix='/api/import')

