from typing import Optional, List
from bson import ObjectId
from datetime import datetime
from models.models import User, UserRegistration, UserLogin, UserStage
from database.config import db_config

class UserRepository:
    def __init__(self):
        self.collection_name = "users"

    def get_collection(self):
        return db_config.get_collection(self.collection_name)

    async def create_user(self, user_data: UserRegistration) -> User:
        """Create a new user"""
        collection = self.get_collection()
        
        # Check if user already exists
        existing_user = await collection.find_one({"name": user_data.name})
        if existing_user:
            raise ValueError("User with this name already exists")
        
        user_dict = user_data.dict()
        user_dict["created_at"] = datetime.utcnow()
        user_dict["updated_at"] = datetime.utcnow()
        user_dict["current_stage"] = UserStage.WELCOME
        user_dict["likelihood_scale"] = ["Low", "Medium", "High"]
        user_dict["impact_scale"] = ["Low", "Medium", "High"]
        
        result = await collection.insert_one(user_dict)
        user_dict["user_id"] = str(result.inserted_id)
        
        return User(**user_dict)

    async def authenticate_user(self, login_data: UserLogin) -> Optional[User]:
        """Authenticate user login"""
        collection = self.get_collection()
        
        user_doc = await collection.find_one({
            "name": login_data.name,
            "password": login_data.password
        })
        
        if user_doc:
            user_doc["user_id"] = str(user_doc["_id"])
            del user_doc["_id"]
            return User(**user_doc)
        return None

    async def get_user_by_id(self, user_id: str) -> Optional[User]:
        """Get user by ID"""
        collection = self.get_collection()
        
        try:
            user_doc = await collection.find_one({"_id": ObjectId(user_id)})
            if user_doc:
                user_doc["user_id"] = str(user_doc["_id"])
                del user_doc["_id"]
                return User(**user_doc)
        except Exception:
            return None
        return None

    async def update_user_stage(self, user_id: str, stage: UserStage) -> bool:
        """Update user's current stage"""
        collection = self.get_collection()
        
        try:
            result = await collection.update_one(
                {"_id": ObjectId(user_id)},
                {
                    "$set": {
                        "current_stage": stage,
                        "updated_at": datetime.utcnow()
                    }
                }
            )
            return result.modified_count > 0
        except Exception:
            return False

    async def update_risk_scales(self, user_id: str, likelihood_scale: List[str], impact_scale: List[str]) -> bool:
        """Update user's likelihood and impact scales"""
        collection = self.get_collection()
        
        try:
            result = await collection.update_one(
                {"_id": ObjectId(user_id)},
                {
                    "$set": {
                        "likelihood_scale": likelihood_scale,
                        "impact_scale": impact_scale,
                        "updated_at": datetime.utcnow()
                    }
                }
            )
            return result.modified_count > 0
        except Exception:
            return False

    async def get_user_scales(self, user_id: str) -> Optional[dict]:
        """Get user's current likelihood and impact scales"""
        collection = self.get_collection()
        
        try:
            user_doc = await collection.find_one(
                {"_id": ObjectId(user_id)},
                {"likelihood_scale": 1, "impact_scale": 1}
            )
            if user_doc:
                return {
                    "likelihood_scale": user_doc.get("likelihood_scale"),
                    "impact_scale": user_doc.get("impact_scale")
                }
        except Exception:
            return None
        return None