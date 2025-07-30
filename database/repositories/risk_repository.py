from typing import List, Optional
from bson import ObjectId
from datetime import datetime
from models.models import GeneratedRisk, FinalizedRisk, RiskStatus
from database.config import db_config

class RiskRepository:
    def __init__(self):
        self.generated_collection = "generated_risks"
        self.finalized_collection = "finalized_risks"

    def get_generated_collection(self):
        return db_config.get_collection(self.generated_collection)

    def get_finalized_collection(self):
        return db_config.get_collection(self.finalized_collection)

    async def save_generated_risks(self, risks: List[GeneratedRisk]) -> List[str]:
        """Save generated risks to database"""
        collection = self.get_generated_collection()
        
        risk_docs = []
        for risk in risks:
            risk_dict = risk.dict(exclude={"risk_id"})
            risk_dict["created_at"] = datetime.utcnow()
            risk_docs.append(risk_dict)
        
        result = await collection.insert_many(risk_docs)
        return [str(id) for id in result.inserted_ids]

    async def get_generated_risks_by_user(self, user_id: str) -> List[GeneratedRisk]:
        """Get all generated risks for a user"""
        collection = self.get_generated_collection()
        
        cursor = collection.find({"user_id": user_id, "status": RiskStatus.GENERATED})
        risks = []
        
        async for doc in cursor:
            doc["risk_id"] = str(doc["_id"])
            del doc["_id"]
            risks.append(GeneratedRisk(**doc))
        
        return risks

    async def get_generated_risk_by_id(self, risk_id: str) -> Optional[GeneratedRisk]:
        """Get a specific generated risk by ID"""
        collection = self.get_generated_collection()
        
        try:
            doc = await collection.find_one({"_id": ObjectId(risk_id)})
            if doc:
                doc["risk_id"] = str(doc["_id"])
                del doc["_id"]
                return GeneratedRisk(**doc)
        except Exception:
            return None
        return None

    async def update_generated_risk(self, risk_id: str, updated_data: dict) -> bool:
        """Update a generated risk"""
        collection = self.get_generated_collection()
        
        try:
            result = await collection.update_one(
                {"_id": ObjectId(risk_id)},
                {"$set": updated_data}
            )
            return result.modified_count > 0
        except Exception:
            return False

    async def finalize_risks(self, risk_ids: List[str], user_id: str) -> List[str]:
        """Move selected risks from generated to finalized"""
        from config import get_logger
        logger = get_logger(__name__)
        
        logger.info(f"Starting risk finalization for user {user_id}, {len(risk_ids)} risks")
        
        # Verify database connection is active
        try:
            from database.config import db_config
            if not db_config.database:
                logger.error("Database connection is not initialized")
                # Try to reconnect
                await db_config.connect()
                logger.info("Reconnected to database")
        except Exception as e:
            logger.error(f"Database connection check failed: {e}")
        
        generated_collection = self.get_generated_collection()
        finalized_collection = self.get_finalized_collection()
        
        # Verify collections are accessible
        logger.info(f"Collections: generated={generated_collection}, finalized={finalized_collection}")
        
        finalized_ids = []
        
        for risk_id in risk_ids:
            try:
                # Get the generated risk
                logger.info(f"Getting generated risk {risk_id}")
                
                try:
                    risk_obj_id = ObjectId(risk_id)
                except Exception as e:
                    logger.error(f"Invalid ObjectId format for risk_id {risk_id}: {e}")
                    continue
                    
                generated_risk = await generated_collection.find_one({"_id": risk_obj_id})
                
                if not generated_risk:
                    logger.warning(f"Generated risk not found: {risk_id}")
                    continue
                
                logger.info(f"Found generated risk: {risk_id}")
                logger.debug(f"Risk data: {generated_risk}")
                
                # Create finalized risk document with error handling for missing fields
                try:
                    finalized_risk = {
                        "user_id": user_id,
                        "description": generated_risk.get("description", "No description provided"),
                        "impact": generated_risk.get("impact", "Medium"),
                        "likelihood": generated_risk.get("likelihood", "Medium"),
                        "treatment_strategy": generated_risk.get("treatment_strategy", "Mitigate"),
                        "treatment_measures": generated_risk.get("treatment_measures", "Measures to be determined"),
                        "status": RiskStatus.FINALIZED,
                        "created_at": datetime.utcnow(),
                        "updated_at": datetime.utcnow()
                    }
                    
                    # Insert into finalized collection
                    logger.info(f"Inserting finalized risk for {risk_id}")
                    result = await finalized_collection.insert_one(finalized_risk)
                    new_id = str(result.inserted_id)
                    finalized_ids.append(new_id)
                    logger.info(f"Successfully finalized risk: {risk_id} -> {new_id}")
                    
                    # Verify the risk was actually saved
                    verification = await finalized_collection.find_one({"_id": result.inserted_id})
                    if verification:
                        logger.info(f"Verified risk {new_id} was saved successfully")
                    else:
                        logger.error(f"Failed to verify risk {new_id} was saved")
                    
                except KeyError as ke:
                    logger.error(f"Missing required field in risk {risk_id}: {ke}")
                    continue
                
            except Exception as e:
                logger.error(f"Error finalizing risk {risk_id}: {e}", exc_info=True)
                continue
        
        logger.info(f"Finalized {len(finalized_ids)} out of {len(risk_ids)} risks")
        return finalized_ids

    async def finalize_risks_with_complete_data(self, risk_data_list: List[dict], user_id: str) -> List[str]:
        """Finalize risks with complete data in one step (combined finalization + data collection)"""
        from config import get_logger
        logger = get_logger(__name__)
        
        logger.info(f"Starting complete risk finalization for user {user_id}, {len(risk_data_list)} risks")
        
        # Verify database connection is active
        try:
            from database.config import db_config
            if not db_config.database:
                logger.error("Database connection is not initialized")
                await db_config.connect()
                logger.info("Reconnected to database")
        except Exception as e:
            logger.error(f"Database connection check failed: {e}")
        
        finalized_collection = self.get_finalized_collection()
        finalized_ids = []
        
        for risk_data in risk_data_list:
            try:
                # Ensure required fields are present
                required_fields = ["description", "impact", "likelihood", "treatment_strategy", "treatment_measures"]
                for field in required_fields:
                    if field not in risk_data or not risk_data[field]:
                        logger.error(f"Missing required field {field} in risk data: {risk_data}")
                        continue
                
                # Parse target_date if provided
                target_date = None
                if risk_data.get("target_date"):
                    try:
                        target_date = datetime.fromisoformat(risk_data["target_date"].replace('Z', '+00:00'))
                    except Exception as e:
                        logger.warning(f"Failed to parse target_date: {risk_data.get('target_date')}, error: {e}")
                
                # Create complete finalized risk document
                finalized_risk = {
                    "user_id": user_id,
                    "description": risk_data["description"],
                    "impact": risk_data["impact"],
                    "likelihood": risk_data["likelihood"],
                    "treatment_strategy": risk_data["treatment_strategy"],
                    "treatment_measures": risk_data["treatment_measures"],
                    # Additional data fields
                    "asset_value": risk_data.get("asset_value"),
                    "department": risk_data.get("department"),
                    "risk_owner": risk_data.get("risk_owner"),
                    "target_date": target_date,
                    "risk_progress": risk_data.get("risk_progress"),
                    "residual_exposure": risk_data.get("residual_exposure"),
                    "status": RiskStatus.FINALIZED,
                    "created_at": datetime.utcnow(),
                    "updated_at": datetime.utcnow()
                }
                
                # Insert into finalized collection
                logger.info(f"Inserting complete finalized risk")
                result = await finalized_collection.insert_one(finalized_risk)
                new_id = str(result.inserted_id)
                finalized_ids.append(new_id)
                logger.info(f"Successfully finalized complete risk: {new_id}")
                
                # Verify the risk was saved
                verification = await finalized_collection.find_one({"_id": result.inserted_id})
                if verification:
                    logger.info(f"Verified complete risk {new_id} was saved successfully")
                else:
                    logger.error(f"Failed to verify complete risk {new_id} was saved")
                    
            except Exception as e:
                logger.error(f"Error finalizing complete risk data {risk_data}: {e}", exc_info=True)
                continue
        
        logger.info(f"Successfully finalized {len(finalized_ids)} complete risks out of {len(risk_data_list)} provided")
        return finalized_ids

    async def get_finalized_risks_by_user(self, user_id: str) -> List[FinalizedRisk]:
        """Get all finalized risks for a user"""
        from config import get_logger
        logger = get_logger(__name__)
        
        collection = self.get_finalized_collection()
        logger.info(f"Retrieving finalized risks for user {user_id}")
        
        try:
            # First check if there are any documents
            count = await collection.count_documents({"user_id": user_id, "status": RiskStatus.FINALIZED})
            logger.info(f"Found {count} finalized risk documents")
            
            cursor = collection.find({"user_id": user_id, "status": RiskStatus.FINALIZED})
            risks = []
            
            async for doc in cursor:
                try:
                    doc["risk_id"] = str(doc["_id"])
                    del doc["_id"]
                    risks.append(FinalizedRisk(**doc))
                except Exception as e:
                    logger.error(f"Error processing risk document: {e}", exc_info=True)
            
            logger.info(f"Successfully retrieved {len(risks)} finalized risks")
            return risks
            
        except Exception as e:
            logger.error(f"Failed to retrieve finalized risks: {e}", exc_info=True)
            return []

    async def update_finalized_risk_additional_data(self, risk_id: str, additional_data: dict) -> bool:
        """Update finalized risk with additional data"""
        collection = self.get_finalized_collection()
        
        try:
            update_data = additional_data.copy()
            update_data["updated_at"] = datetime.utcnow()
            
            result = await collection.update_one(
                {"_id": ObjectId(risk_id)},
                {"$set": update_data}
            )
            return result.modified_count > 0
        except Exception:
            return False

    async def get_finalized_risks_count(self, user_id: str) -> int:
        """Get count of finalized risks for a user"""
        from config import get_logger
        logger = get_logger(__name__)
        
        collection = self.get_finalized_collection()
        try:
            count = await collection.count_documents({"user_id": user_id, "status": RiskStatus.FINALIZED})
            logger.info(f"Found {count} finalized risks for user {user_id}")
            
            # Additional debug info - show a sample of the risks
            if count > 0:
                sample = await collection.find({"user_id": user_id, "status": RiskStatus.FINALIZED}).limit(1).to_list(1)
                if sample:
                    risk_sample = sample[0]
                    risk_sample["_id"] = str(risk_sample["_id"])  # Convert ObjectId to string for logging
                    logger.info(f"Sample risk: {risk_sample}")
            return count
        except Exception as e:
            logger.error(f"Error counting finalized risks: {e}", exc_info=True)
            return 0

    async def delete_generated_risk(self, risk_id: str) -> bool:
        """Delete a generated risk"""
        collection = self.get_generated_collection()
        
        try:
            result = await collection.delete_one({"_id": ObjectId(risk_id)})
            return result.deleted_count > 0
        except Exception:
            return False

    async def get_finalized_risk_by_id(self, risk_id: str) -> Optional[FinalizedRisk]:
        """Get a specific finalized risk by ID"""
        collection = self.get_finalized_collection()
        
        try:
            doc = await collection.find_one({"_id": ObjectId(risk_id)})
            if doc:
                doc["risk_id"] = str(doc["_id"])
                del doc["_id"]
                return FinalizedRisk(**doc)
        except Exception:
            return None
        return None