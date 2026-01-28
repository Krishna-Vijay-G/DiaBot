"""
DiaBot Backend Server Entry Point

Run this file to start the DiaBot backend server.

Usage:
    python backend/run.py
"""

import os
import sys

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.main import create_app

# Create application instance
app = create_app()


if __name__ == "__main__":
    # Get configuration from environment
    host = os.environ.get('HOST', '0.0.0.0')
    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('FLASK_DEBUG', 'false').lower() == 'true'
    
    print(f"""
╔══════════════════════════════════════════════════════════════════╗
║                     DiaBot Backend Server                        ║
╠══════════════════════════════════════════════════════════════════╣
║  AI-Powered Diabetes Screening Platform                          ║
║                                                                  ║
║  Modules:                                                        ║
║  • Prediction Module: LightGBM (98.1% accuracy)                  ║
║  • Advisory Module: LLM-powered chatbot                          ║
║  • User Module: Session management                               ║
║                                                                  ║
║  Server: http://{host}:{port}                                    ║
║  API: http://{host}:{port}/api/v1                                ║
╚══════════════════════════════════════════════════════════════════╝
    """)
    
    app.run(host=host, port=port, debug=debug, use_reloader=False)
