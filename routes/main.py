"""Main page routes"""
from flask import Blueprint, render_template

from config import get_app_version

main_bp = Blueprint('main', __name__)

@main_bp.route('/')
def index():
    app_version = get_app_version()
    return render_template('index.html', version=app_version)

