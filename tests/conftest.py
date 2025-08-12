import pytest
import asyncio
from httpx import AsyncClient
from app.main import app
from app.core.config import settings
from app.core.database import connect_to_mongo, close_mongo_connection, db
from app.core.cache import cache_manager
import os


# Test configuration
settings.mongodb_database = "test_customer_support_chatbot"
settings.redis_db = 1  # Use different Redis DB for tests


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
async def setup_test_db():
    """Set up test database"""
    await connect_to_mongo()
    
    # Clean test database
    if db.database:
        await db.database.drop_collection("chat_history")
        await db.database.drop_collection("user_context")
        await db.database.drop_collection("intent_logs")
    
    yield
    
    # Cleanup
    if db.database:
        await db.database.drop_collection("chat_history")
        await db.database.drop_collection("user_context")
        await db.database.drop_collection("intent_logs")
    
    await close_mongo_connection()


@pytest.fixture(scope="session")
async def setup_test_cache():
    """Set up test cache"""
    await cache_manager.connect()
    
    # Clear test cache
    if cache_manager.redis:
        await cache_manager.redis.flushdb()
    
    yield
    
    # Cleanup
    if cache_manager.redis:
        await cache_manager.redis.flushdb()
    
    await cache_manager.disconnect()


@pytest.fixture
async def client(setup_test_db, setup_test_cache):
    """Create test client"""
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac


@pytest.fixture
def sample_chat_message():
    """Sample chat message for testing"""
    return {
        "message": "I need help with my order",
        "user_id": "test_user_123",
        "channel": "web"
    }


@pytest.fixture
def sample_order_inquiry():
    """Sample order inquiry message"""
    return {
        "message": "Where is my order #12345?",
        "user_id": "test_user_456",
        "channel": "web"
    }


@pytest.fixture
def sample_account_inquiry():
    """Sample account inquiry message"""
    return {
        "message": "I need to update my email address",
        "user_id": "test_user_789",
        "channel": "web"
    }


@pytest.fixture
def sample_escalation_message():
    """Sample message that should trigger escalation"""
    return {
        "message": "I'm very angry and want to speak to a manager immediately!",
        "user_id": "test_user_escalation",
        "channel": "web"
    }
