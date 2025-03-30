"""
Debug utility for tracking authentication issues
"""
import logging
from models import users_db

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def debug_users():
    """Print all users in the database for debugging"""
    logger.info("==== USER DATABASE CONTENTS ====")
    
    for username, data in users_db.items():
        # Mask password for security
        masked_password = "********" if data.get('password') else "None"
        
        logger.info(f"User: {username}")
        logger.info(f"  Password: {masked_password}")
        logger.info(f"  Plan: {data.get('plan', 'Unknown')}")
        logger.info(f"  Joined: {data.get('joined_date', 'Unknown')}")
        logger.info(f"  Payment: {data.get('payment_status', 'Unknown')}")
        logger.info("------------------------------")
        
    logger.info(f"Total users: {len(users_db)}")
    logger.info("================================")
