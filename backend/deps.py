"""Shared dependencies: MongoDB client, env config, and re-exports.

This module exists so router files can `from deps import db, COOKIE_SECURE, ...`
without circular imports against server.py.
"""
import os
import logging
from motor.motor_asyncio import AsyncIOMotorClient

# MongoDB connection (single client shared across the app)
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# Phase D: configurable security & business policy
COOKIE_SECURE = os.environ.get('COOKIE_SECURE', 'false').lower() == 'true'
COOKIE_SAMESITE = 'none' if COOKIE_SECURE else 'lax'
BOOKING_HOLD_DAYS = int(os.environ.get('BOOKING_HOLD_DAYS', '7'))

# Shared logger
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("sipro")

# Re-export auth helpers so routers import from one place
from auth import (  # noqa: F401
    hash_password, verify_password, create_access_token,
    create_refresh_token, get_current_user, get_jwt_secret,
    generate_reset_token, JWT_ALGORITHM,
)
