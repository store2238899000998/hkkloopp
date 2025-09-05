#!/usr/bin/env python3
"""
Production deployment script for the Investment Telegram Bot
"""

import os
import sys
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def main():
    """Main deployment function"""
    print("🚀 Starting Investment Telegram Bot deployment...")
    
    try:
        # Import and run the main application
        from main import app
        import uvicorn
        
        print("✅ Application loaded successfully")
        print("🌐 Starting web server...")
        
        # Run the FastAPI app
        uvicorn.run(
            app,
            host="0.0.0.0",
            port=int(os.environ.get("PORT", 8000)),
            log_level="info"
        )
        
    except Exception as e:
        print(f"❌ Deployment failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
