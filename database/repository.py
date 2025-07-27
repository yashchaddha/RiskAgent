from typing import Optional, List
from bson import ObjectId
from datetime import datetime
from motor.motor_asyncio import AsyncIOMotorDatabase
from database.connection import get_database
from models.user_model import UserModel
from models.risk_model import RiskRegister
from graph.state.graph_state import GraphState
import logging

logger = logging.getLogger(__name__)

class UserRepository:
    def __init__(self):
        self._db = None
        self._collection = None

    @property
    def db(self):
        if self._db is None:
            self._db = get_database()
        return self._db

    @property  
    def collection(self):
        if self._collection is None:
            if self.db is not None:
                self._collection = self.db.users
        return self._collection

    async def create_user(self, user: UserModel) -> UserModel:
        """Create a new user"""
        user_dict = user.dict(by_alias=True, exclude_unset=True)
        result = await self.collection.insert_one(user_dict)
        user.id = result.inserted_id
        return user

    async def get_user_by_username(self, username: str) -> Optional[UserModel]:
        """Get user by username"""
        user_doc = await self.collection.find_one({"username": username})
        if user_doc:
            return UserModel(**user_doc)
        return None

    async def get_user_by_id(self, user_id: ObjectId) -> Optional[UserModel]:
        """Get user by ID"""
        user_doc = await self.collection.find_one({"_id": user_id})
        if user_doc:
            return UserModel(**user_doc)
        return None

    async def update_last_login(self, user_id: ObjectId) -> bool:
        """Update user's last login timestamp"""
        result = await self.collection.update_one(
            {"_id": user_id},
            {"$set": {"last_login": datetime.utcnow()}}
        )
        return result.modified_count > 0

class SessionRepository:
    def __init__(self):
        self._db = None
        self._collection = None

    @property
    def db(self):
        if self._db is None:
            self._db = get_database()
        return self._db

    @property  
    def collection(self):
        if self._collection is None:
            if self.db is not None:
                self._collection = self.db.sessions
        return self._collection

    async def create_graph_state(self, graph_state: GraphState) -> GraphState:
        """Create a new graph state/session"""
        graph_state_dict = graph_state.dict(by_alias=True, exclude_unset=True)
        result = await self.collection.insert_one(graph_state_dict)
        graph_state.id = result.inserted_id
        return graph_state

    async def get_active_graph_state_by_user(self, user_id: ObjectId) -> Optional[GraphState]:
        """Get active graph state for user"""
        graph_state_doc = await self.collection.find_one({
            "user_id": user_id,
        })
        if graph_state_doc:
            return GraphState(**graph_state_doc)
        return None

    async def get_graph_state_by_id(self, graph_state_id: ObjectId) -> Optional[GraphState]:
        """Get graph state by ID"""
        graph_state_doc = await self.collection.find_one({"_id": graph_state_id})
        if graph_state_doc:
            return GraphState(**graph_state_doc)
        return None

    async def update_graph_state(self, graph_state: GraphState) -> bool:
        """Update graph state"""
        if not graph_state.id:
            logger.error("❌ Cannot update GraphState: No ID found")
            return False
            
        # Update timestamps
        graph_state.updated_at = datetime.utcnow()
        graph_state.last_activity = datetime.utcnow()
        
        graph_state_dict = graph_state.dict(by_alias=True, exclude_unset=True)
        logger.info(f"🔄 Updating GraphState with ID: {graph_state.id}")
        logger.debug(f"🔄 Update data: {list(graph_state_dict.keys())}")
        
        result = await self.collection.replace_one(
            {"_id": graph_state.id},
            graph_state_dict
        )
        
        success = result.modified_count > 0
        if success:
            logger.info(f"✅ Successfully updated GraphState for user: {graph_state.username}")
        else:
            logger.warning(f"⚠️ No documents were modified for ID: {graph_state.id}")
            
        return success

    async def deactivate_graph_state(self, graph_state_id: ObjectId) -> bool:
        """Deactivate graph state"""
        result = await self.collection.update_one(
            {"_id": graph_state_id},
            {"$set": {"is_active": False, "updated_at": datetime.utcnow()}}
        )
        return result.modified_count > 0

    async def cleanup_expired_graph_states(self, timeout_minutes: int = 60) -> int:
        """Clean up expired graph states"""
        cutoff_time = datetime.utcnow().timestamp() - (timeout_minutes * 60)
        cutoff_datetime = datetime.fromtimestamp(cutoff_time)
        
        result = await self.collection.update_many(
            {
                "last_activity": {"$lt": cutoff_datetime},
            },
            {"$set": {"is_active": False}}
        )
        return result.modified_count

    async def get_graph_state_by_username(self, username: str) -> Optional[GraphState]:
        """Get active graph state by username"""
        graph_state_doc = await self.collection.find_one({
            "username": username,
        })
        if graph_state_doc:
            return GraphState(**graph_state_doc)
        return None

class RiskRegisterRepository:
    def __init__(self):
        self._db = None
        self._collection = None

    @property
    def db(self):
        if self._db is None:
            self._db = get_database()
        return self._db

    @property  
    def collection(self):
        if self._collection is None:
            if self.db is not None:
                self._collection = self.db.risk_registers
        return self._collection

    async def create_risk_register(self, risk_register: RiskRegister) -> RiskRegister:
        """Create a new risk register"""
        risk_register_dict = risk_register.dict(by_alias=True, exclude_unset=True)
        result = await self.collection.insert_one(risk_register_dict)
        risk_register.id = result.inserted_id
        return risk_register

    async def get_risk_register_by_id(self, register_id: ObjectId) -> Optional[RiskRegister]:
        """Get risk register by ID"""
        register_doc = await self.collection.find_one({"_id": register_id})
        if register_doc:
            return RiskRegister(**register_doc)
        return None

    async def update_risk_register(self, risk_register: RiskRegister) -> bool:
        """Update risk register with optimistic locking"""
        current_version = risk_register.version_id
        risk_register.version_id += 1
        risk_register.updated_at = datetime.utcnow()
        
        risk_register_dict = risk_register.dict(by_alias=True, exclude_unset=True)
        
        result = await self.collection.replace_one(
            {"_id": risk_register.id, "version_id": current_version},
            risk_register_dict
        )
        
        if result.modified_count == 0:
            logger.warning(f"Optimistic locking failed for risk register {risk_register.id}")
            return False
        
        return True

    async def get_risk_registers_by_user(self, user_id: ObjectId) -> List[RiskRegister]:
        """Get all risk registers created by user"""
        cursor = self.collection.find({"created_by.user_id": user_id})
        registers = []
        async for doc in cursor:
            registers.append(RiskRegister(**doc))
        return registers

    async def delete_risk_register(self, register_id: ObjectId) -> bool:
        """Delete risk register"""
        result = await self.collection.delete_one({"_id": register_id})
        return result.deleted_count > 0

# Repository instances
user_repository = UserRepository()
session_repository = SessionRepository() 
risk_register_repository = RiskRegisterRepository()
