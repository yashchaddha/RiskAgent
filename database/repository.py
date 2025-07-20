# database/repository.py
from typing import Optional, List
from datetime import datetime
import logging
from pymongo.errors import PyMongoError, DuplicateKeyError

from database.connection import get_users_collection, get_risks_collection
from models.user_models import User
from models.risk_models import RiskItem

logger = logging.getLogger(__name__)

class Repository:
    """Simple repository for users and risks only"""
    
    # USER OPERATIONS
    
    async def create_user(self, user: User) -> bool:
        """Create a new user"""
        try:
            collection = await get_users_collection()
            user_data = user.model_dump()
            user_data["_id"] = user.id
            
            await collection.insert_one(user_data)
            logger.info(f"✓ User created: {user.username}")
            return True
            
        except DuplicateKeyError:
            logger.warning(f"⚠️ User already exists: {user.username}")
            return False
        except PyMongoError as e:
            logger.error(f"❌ Failed to create user {user.username}: {e}")
            return False
    
    async def get_user_by_username(self, username: str) -> Optional[User]:
        """Get user by username"""
        try:
            collection = await get_users_collection()
            user_data = await collection.find_one({"username": username})
            
            if user_data:
                user_id = user_data.pop("_id")
                user_data["id"] = user_id
                return User(**user_data)
            return None
            
        except PyMongoError as e:
            logger.error(f"❌ Failed to get user by username {username}: {e}")
            return None
    
    # RISK OPERATIONS
    
    async def create_risk(self, risk: RiskItem) -> bool:
        """Create a new risk"""
        try:
            collection = await get_risks_collection()
            risk_data = risk.model_dump()
            risk_data["_id"] = risk.risk_id
            
            await collection.insert_one(risk_data)
            logger.info(f"✓ Risk created: {risk.risk_id} by {risk.username}")
            return True
            
        except DuplicateKeyError:
            logger.warning(f"⚠️ Risk already exists: {risk.risk_id}")
            return False
        except PyMongoError as e:
            logger.error(f"❌ Failed to create risk {risk.risk_id}: {e}")
            return False
    
    async def update_risk(self, risk: RiskItem) -> bool:
        """Update an existing risk"""
        try:
            collection = await get_risks_collection()
            risk_data = risk.model_dump()
            risk_data["updated_at"] = datetime.now()
            risk_data["_id"] = risk.risk_id
            
            result = await collection.replace_one(
                {"_id": risk.risk_id},
                risk_data
            )
            
            if result.modified_count > 0:
                logger.info(f"✓ Risk updated: {risk.risk_id}")
                return True
            return False
            
        except PyMongoError as e:
            logger.error(f"❌ Failed to update risk {risk.risk_id}: {e}")
            return False
    
    async def get_risk(self, risk_id: str) -> Optional[RiskItem]:
        """Get risk by ID"""
        try:
            collection = await get_risks_collection()
            risk_data = await collection.find_one({"_id": risk_id})
            
            if risk_data:
                risk_data.pop("_id", None)
                return RiskItem(**risk_data)
            return None
            
        except PyMongoError as e:
            logger.error(f"❌ Failed to get risk {risk_id}: {e}")
            return None
    
    async def get_user_risks(self, username: str) -> List[RiskItem]:
        """Get all risks created by a user"""
        try:
            collection = await get_risks_collection()
            cursor = collection.find({"username": username}).sort("created_at", -1)
            
            risks = []
            async for risk_data in cursor:
                risk_data.pop("_id", None)
                risks.append(RiskItem(**risk_data))
            
            return risks
            
        except PyMongoError as e:
            logger.error(f"❌ Failed to get user risks for {username}: {e}")
            return []
    
    async def get_approved_risks(self, username: str) -> List[RiskItem]:
        """Get approved risks by a user"""
        try:
            collection = await get_risks_collection()
            cursor = collection.find({
                "username": username,
                "is_approved": True
            }).sort("created_at", -1)
            
            risks = []
            async for risk_data in cursor:
                risk_data.pop("_id", None)
                risks.append(RiskItem(**risk_data))
            
            return risks
            
        except PyMongoError as e:
            logger.error(f"❌ Failed to get approved risks for {username}: {e}")
            return []
    
    async def delete_risk(self, risk_id: str) -> bool:
        """Delete a risk"""
        try:
            collection = await get_risks_collection()
            result = await collection.delete_one({"_id": risk_id})
            
            if result.deleted_count > 0:
                logger.info(f"✓ Risk deleted: {risk_id}")
                return True
            return False
            
        except PyMongoError as e:
            logger.error(f"❌ Failed to delete risk {risk_id}: {e}")
            return False

repository = Repository()