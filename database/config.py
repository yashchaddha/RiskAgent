import os
from motor.motor_asyncio import AsyncIOMotorClient
from pymongo import MongoClient
from typing import Optional

class DatabaseConfig:
    def __init__(self):
        self.mongodb_url = os.getenv("MONGODB_URL", "mongodb://localhost:27017")
        self.database_name = os.getenv("DATABASE_NAME", "risk_management")
        self.client: Optional[AsyncIOMotorClient] = None
        self.database = None

    async def connect(self):
        """Connect to MongoDB"""
        self.client = AsyncIOMotorClient(self.mongodb_url)
        self.database = self.client[self.database_name]
        
        # Test connection
        try:
            await self.client.admin.command('ping')
            print("Connected to MongoDB successfully")
        except Exception as e:
            print(f"Failed to connect to MongoDB: {e}")
            raise

    async def disconnect(self):
        """Disconnect from MongoDB"""
        if self.client:
            self.client.close()
            print("Disconnected from MongoDB")

    def get_database(self):
        """Get database instance"""
        return self.database

    def get_collection(self, collection_name: str):
        """Get collection instance"""
        return self.database[collection_name]

# Global database instance
db_config = DatabaseConfig()