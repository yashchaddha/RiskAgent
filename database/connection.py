# database/connection.py
import motor.motor_asyncio
from pymongo import MongoClient
from config.settings import settings
import logging

logger = logging.getLogger(__name__)

class DatabaseManager:
    """Simple database connection manager for MongoDB"""
    
    def __init__(self):
        self.client = None
        self.database = None
        self.async_client = None
        self.async_database = None
    
    def connect(self):
        """Establish synchronous MongoDB connection"""
        try:
            self.client = MongoClient(settings.MONGODB_URL)
            self.database = self.client[settings.MONGODB_DATABASE]
            
            # Test connection
            self.client.admin.command('ping')
            logger.info(f"✓ Connected to MongoDB: {settings.MONGODB_URL}/{settings.MONGODB_DATABASE}")
            
            # Create indexes
            # self._create_indexes()
            
        except Exception as e:
            logger.error(f"❌ Failed to connect to MongoDB: {e}")
            raise
    
    async def connect_async(self):
        """Establish asynchronous MongoDB connection"""
        try:
            self.async_client = motor.motor_asyncio.AsyncIOMotorClient(settings.MONGODB_URL)
            self.async_database = self.async_client[settings.MONGODB_DATABASE]
            
            # Test connection
            await self.async_client.admin.command('ping')
            logger.info(f"✓ Connected to MongoDB (async): {settings.MONGODB_URL}/{settings.MONGODB_DATABASE}")
            
        except Exception as e:
            logger.error(f"❌ Failed to connect to MongoDB (async): {e}")
            raise
    
    def _create_indexes(self):
        """Create necessary database indexes"""
        try:
            # Users collection
            self.database.users.create_index("username", unique=True)
            
            # Risks collection
            self.database.risks.create_index("risk_id", unique=True)
            self.database.risks.create_index("username")
            self.database.risks.create_index("category")
            self.database.risks.create_index("status")
            self.database.risks.create_index("created_at")
            
            logger.info("✓ Database indexes created successfully")
            
        except Exception as e:
            logger.error(f"❌ Failed to create indexes: {e}")
    
    def close(self):
        """Close database connections"""
        if self.client:
            self.client.close()
        if self.async_client:
            self.async_client.close()
        logger.info("✓ Database connections closed")

# Global database manager instance
db_manager = DatabaseManager()

def get_database():
    """Get synchronous database instance"""
    if not db_manager.database:
        db_manager.connect()
    return db_manager.database

async def get_async_database():
    """Get asynchronous database instance"""
    if not db_manager.async_database:
        await db_manager.connect_async()
    return db_manager.async_database

# Simple collection getters
async def get_users_collection():
    """Get users collection"""
    db = await get_async_database()
    return db.users

async def get_risks_collection():
    """Get risks collection"""
    db = await get_async_database()
    return db.risks