from typing import Optional, List
from bson import ObjectId
from datetime import datetime
from models.models import RiskReport
from database.config import db_config

class ReportRepository:
    def __init__(self):
        self.collection_name = "risk_reports"

    def get_collection(self):
        return db_config.get_collection(self.collection_name)

    async def create_report(self, report_data: RiskReport) -> str:
        """Create a new risk report"""
        collection = self.get_collection()
        
        report_dict = report_data.dict(exclude={"report_id"})
        report_dict["generated_at"] = datetime.utcnow()
        
        result = await collection.insert_one(report_dict)
        return str(result.inserted_id)

    async def get_report_by_id(self, report_id: str) -> Optional[RiskReport]:
        """Get a risk report by ID"""
        collection = self.get_collection()
        
        try:
            doc = await collection.find_one({"_id": ObjectId(report_id)})
            if doc:
                doc["report_id"] = str(doc["_id"])
                del doc["_id"]
                return RiskReport(**doc)
        except Exception:
            return None
        return None

    async def get_reports_by_user(self, user_id: str) -> List[RiskReport]:
        """Get all reports for a user"""
        collection = self.get_collection()
        
        cursor = collection.find({"user_id": user_id}).sort("generated_at", -1)
        reports = []
        
        async for doc in cursor:
            doc["report_id"] = str(doc["_id"])
            del doc["_id"]
            reports.append(RiskReport(**doc))
        
        return reports

    async def get_latest_report_by_user(self, user_id: str) -> Optional[RiskReport]:
        """Get the latest report for a user"""
        collection = self.get_collection()
        
        doc = await collection.find_one(
            {"user_id": user_id},
            sort=[("generated_at", -1)]
        )
        
        if doc:
            doc["report_id"] = str(doc["_id"])
            del doc["_id"]
            return RiskReport(**doc)
        return None

    async def delete_report(self, report_id: str) -> bool:
        """Delete a risk report"""
        collection = self.get_collection()
        
        try:
            result = await collection.delete_one({"_id": ObjectId(report_id)})
            return result.deleted_count > 0
        except Exception:
            return False