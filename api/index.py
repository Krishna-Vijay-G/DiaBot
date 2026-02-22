"""
Vercel Serverless Function Entry Point for DiaBot

This file serves as the entry point for Vercel's Python serverless functions.
"""

import os
import sys

# Add the project root to the path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

# Set environment variables for Vercel deployment
os.environ.setdefault('FLASK_ENV', 'production')

from backend.main import create_app

# Create the Flask application
app = create_app()

# Vercel expects this handler
def handler(request):
    """Handle incoming requests for Vercel serverless"""
    return app(request.environ, request.start_response)
