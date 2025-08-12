from motor.motor_asyncio import AsyncIOMotorClient
from pymongo import MongoClient
from .config import settings
import logging

logger = logging.getLogger(__name__)


class Database:
    client: AsyncIOMotorClient = None
    database = None


# MongoDB connection instance
db = Database()


async def connect_to_mongo():
    """Create database connection"""
    try:
        db.client = AsyncIOMotorClient(settings.mongodb_url)
        db.database = db.client[settings.mongodb_database]
        
        # Test the connection
        await db.client.admin.command('ping')
        logger.info("Successfully connected to MongoDB")
        
        # Create indexes for chat history collection
        await create_indexes()
        
    except Exception as e:
        logger.error(f"Failed to connect to MongoDB: {e}")
        raise


async def close_mongo_connection():
    """Close database connection"""
    if db.client:
        db.client.close()
        logger.info("Disconnected from MongoDB")


async def create_indexes():
    """Create database indexes for optimal performance"""
    try:
        # Chat history indexes
        await db.database.chat_history.create_index([("user_id", 1), ("timestamp", -1)])
        await db.database.chat_history.create_index([("session_id", 1)])
        await db.database.chat_history.create_index([("timestamp", -1)])
        
        # User context indexes
        await db.database.user_context.create_index([("user_id", 1)])
        await db.database.user_context.create_index([("updated_at", 1)])
        
        # Intent logs indexes
        await db.database.intent_logs.create_index([("intent", 1)])
        await db.database.intent_logs.create_index([("confidence", -1)])
        await db.database.intent_logs.create_index([("timestamp", -1)])
        
        logger.info("Database indexes created successfully")
        
    except Exception as e:
        logger.warning(f"Failed to create indexes: {e}")


def get_database():
    """Get database instance"""
    return db.database


# Collections
def get_chat_history_collection():
    """Get chat history collection"""
    return db.database.chat_history


def get_user_context_collection():
    """Get user context collection"""
    return db.database.user_context


def get_intent_logs_collection():
    """Get intent logs collection"""
    return db.database.intent_logs