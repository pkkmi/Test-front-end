"""
This file is a simple deployment helper that will be imported at the beginning of app.py
to verify that code changes are being properly deployed to Railway.
"""

import os
import sys
import logging
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("deploy_helper")

# Print deployment verification marker
logger.warning(f"DEPLOYMENT CHECK: Code updated at 2025-04-05 11:10 UTC")
logger.warning(f"DEPLOYMENT CHECK: Running on Python {sys.version}")

# Print critical environment information
env_vars = {
    "PORT": os.environ.get("PORT", "Not set"),
    "GOOGLE_CLIENT_SECRET_SET": bool(os.environ.get("GOOGLE_CLIENT_SECRET")),
    "RAILWAY_DEPLOYMENT_ID": os.environ.get("RAILWAY_DEPLOYMENT_ID", "Not set")[:8] + "...",
    "RAILWAY_GIT_COMMIT_SHA": os.environ.get("RAILWAY_GIT_COMMIT_SHA", "Not set")[:8] + "...",
}

logger.warning(f"DEPLOYMENT CHECK: Environment variables: {env_vars}")

# Print paths for diagnostic purposes
module_paths = [p for p in sys.path if "app" in p or "site-packages" in p]
logger.warning(f"DEPLOYMENT CHECK: Key module paths: {module_paths}")

# Check if MongoDB client is installed
try:
    import pymongo
    logger.warning(f"DEPLOYMENT CHECK: pymongo version {pymongo.__version__} is installed")
except ImportError:
    logger.warning("DEPLOYMENT CHECK: pymongo is NOT installed")

# Check if the files are present
files_to_check = [
    "/app/app.py", 
    "/app/backend/db_fallback.py",
    "/app/backend/oauth.py"
]

for file_path in files_to_check:
    if os.path.exists(file_path):
        size = os.path.getsize(file_path)
        mtime = datetime.fromtimestamp(os.path.getmtime(file_path))
        logger.warning(f"DEPLOYMENT CHECK: {file_path} exists, size: {size} bytes, modified: {mtime}")
    else:
        logger.warning(f"DEPLOYMENT CHECK: {file_path} DOES NOT EXIST")

# Print a success message
logger.warning("DEPLOYMENT CHECK: Helper successfully loaded - this is the new version!")
