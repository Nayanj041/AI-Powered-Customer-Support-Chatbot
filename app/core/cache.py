import redis.asyncio as redis
import json
import pickle
from typing import Any, Optional, Union
from .config import settings
import logging

logger = logging.getLogger(__name__)


class MockRedis:
    """Mock Redis client for development without Redis server"""
    
    def __init__(self):
        self.data = {}
    
    async def ping(self):
        return True
    
    async def get(self, key: str):
        return self.data.get(key)
    
    async def setex(self, key: str, ttl: int, value: Any):
        self.data[key] = value
        return True
    
    async def delete(self, key: str):
        if key in self.data:
            del self.data[key]
        return True
    
    async def exists(self, key: str):
        return 1 if key in self.data else 0
    
    async def incrby(self, key: str, amount: int = 1):
        if key not in self.data:
            self.data[key] = '0'
        current = int(self.data[key])
        new_value = current + amount
        self.data[key] = str(new_value)
        return new_value
    
    async def expire(self, key: str, ttl: int):
        return True
    
    async def close(self):
        pass


class CacheManager:
    def __init__(self):
        self.redis: Optional[Union[redis.Redis, MockRedis]] = None
    
    async def connect(self):
        """Connect to Redis"""
        try:
            self.redis = redis.from_url(
                settings.redis_url,
                db=settings.redis_db,
                encoding="utf-8",
                decode_responses=True
            )
            # Test the connection
            await self.redis.ping()
            logger.info("Successfully connected to Redis")
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}")
            # Create a mock redis for development without Redis
            logger.warning("Using mock Redis client for development")
            self.redis = MockRedis()
    
    async def disconnect(self):
        """Disconnect from Redis"""
        if self.redis and hasattr(self.redis, 'close'):
            await self.redis.close()
            logger.info("Disconnected from Redis")
    
    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache"""
        try:
            if not self.redis:
                return None
            
            value = await self.redis.get(key)
            if value is None:
                return None
            
            # Try to parse as JSON first, fallback to string
            try:
                return json.loads(value)
            except json.JSONDecodeError:
                return value
                
        except Exception as e:
            logger.error(f"Error getting cache key {key}: {e}")
            return None
    
    async def set(
        self, 
        key: str, 
        value: Any, 
        ttl: Optional[int] = None
    ) -> bool:
        """Set value in cache"""
        try:
            if not self.redis:
                return False
            
            # Serialize complex objects as JSON
            if isinstance(value, (dict, list)):
                value = json.dumps(value)
            elif not isinstance(value, (str, int, float)):
                value = str(value)
            
            ttl = ttl or settings.cache_ttl
            await self.redis.setex(key, ttl, value)
            return True
            
        except Exception as e:
            logger.error(f"Error setting cache key {key}: {e}")
            return False
    
    async def delete(self, key: str) -> bool:
        """Delete key from cache"""
        try:
            if not self.redis:
                return False
            
            await self.redis.delete(key)
            return True
            
        except Exception as e:
            logger.error(f"Error deleting cache key {key}: {e}")
            return False
    
    async def exists(self, key: str) -> bool:
        """Check if key exists in cache"""
        try:
            if not self.redis:
                return False
            
            return await self.redis.exists(key) > 0
            
        except Exception as e:
            logger.error(f"Error checking cache key {key}: {e}")
            return False
    
    async def increment(self, key: str, amount: int = 1) -> Optional[int]:
        """Increment counter in cache"""
        try:
            if not self.redis:
                return None
            
            return await self.redis.incrby(key, amount)
            
        except Exception as e:
            logger.error(f"Error incrementing cache key {key}: {e}")
            return None
    
    # Specialized cache methods for chatbot
    
    async def cache_user_context(self, user_id: str, context: dict, ttl: int = 1800):
        """Cache user conversation context"""
        key = f"user_context:{user_id}"
        return await self.set(key, context, ttl)
    
    async def get_user_context(self, user_id: str) -> Optional[dict]:
        """Get cached user context"""
        key = f"user_context:{user_id}"
        return await self.get(key)
    
    async def cache_salesforce_data(self, customer_id: str, data: dict, ttl: int = 600):
        """Cache Salesforce customer data"""
        key = f"salesforce:{customer_id}"
        return await self.set(key, data, ttl)
    
    async def get_salesforce_data(self, customer_id: str) -> Optional[dict]:
        """Get cached Salesforce data"""
        key = f"salesforce:{customer_id}"
        return await self.get(key)
    
    async def cache_frequent_query(self, query_hash: str, response: str, ttl: int = 3600):
        """Cache response for frequent queries"""
        key = f"frequent_query:{query_hash}"
        return await self.set(key, response, ttl)
    
    async def get_frequent_query_response(self, query_hash: str) -> Optional[str]:
        """Get cached response for frequent query"""
        key = f"frequent_query:{query_hash}"
        return await self.get(key)
    
    async def increment_query_count(self, query_hash: str) -> Optional[int]:
        """Increment query frequency counter"""
        key = f"query_count:{query_hash}"
        count = await self.increment(key)
        if count and count == 1:
            # Set TTL for new counters
            await self.redis.expire(key, 86400)  # 24 hours
        return count


# Global cache manager instance
cache_manager = CacheManager()