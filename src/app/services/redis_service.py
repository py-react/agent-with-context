import redis.asyncio as redis
import os
from typing import Optional, Dict, Any
import json

class RedisService:
    def __init__(self):
        self.redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
        self.redis_client: Optional[redis.Redis] = None
    
    async def connect(self):
        """Initialize Redis connection"""
        if not self.redis_client:
            self.redis_client = redis.from_url(self.redis_url, decode_responses=True)
            await self.redis_client.ping()
            print("✅ Redis connected successfully")
    
    async def disconnect(self):
        """Close Redis connection"""
        if self.redis_client:
            await self.redis_client.close()
            print("✅ Redis disconnected successfully")
    
    async def test_connection(self) -> bool:
        """Test if Redis connection is working"""
        try:
            await self.connect()
            await self.redis_client.ping()
            return True
        except Exception as e:
            print(f"❌ Redis connection failed: {e}")
            return False
    
    async def set_key(self, key: str, value: str, ttl: int = 3600) -> bool:
        """Set a key with TTL"""
        try:
            await self.connect()
            await self.redis_client.setex(key, ttl, value)
            return True
        except Exception as e:
            print(f"Error setting key {key}: {e}")
            return False
    
    async def get_key(self, key: str) -> Optional[str]:
        """Get a key value"""
        try:
            await self.connect()
            return await self.redis_client.get(key)
        except Exception as e:
            print(f"Error getting key {key}: {e}")
            return None
    
    async def delete_key(self, key: str) -> bool:
        """Delete a key"""
        try:
            await self.connect()
            await self.redis_client.delete(key)
            return True
        except Exception as e:
            print(f"Error deleting key {key}: {e}")
            return False

 