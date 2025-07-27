from fastapi import APIRouter, HTTPException, Response
from fastapi.responses import FileResponse
from bson import ObjectId
from database.repository import risk_register_repository
from services.report_service import generate_report
import logging
import tempfile
import os

logger = logging.getLogger(__name__)
router = APIRouter()

@router.get("/reports/register/{register_id}")
async def generate_risk_register_report(register_id: str, format: str = "pdf"):
    """Generate a report for a risk register"""
    try:
        # Get the risk register
        register = await risk_register_repository.get_risk_register_by_id(ObjectId(register_id))
        if not register:
            raise HTTPException(status_code=404, detail="Risk register not found")
            
        # Generate the report
        if format.lower() not in ["pdf", "html"]:
            raise HTTPException(status_code=400, detail="Format must be 'pdf' or 'html'")
            
        report_content = await generate_report(register, format.lower())
        
        if format.lower() == "html":
            return Response(
                content=report_content,
                media_type="text/html",
                headers={"Content-Disposition": f"attachment; filename=risk_register_{register_id}.html"}
            )
        else:
            # For PDF, create a temporary file
            with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file:
                tmp_file.write(report_content)
                tmp_file_path = tmp_file.name
                
            return FileResponse(
                path=tmp_file_path,
                media_type="application/pdf",
                filename=f"risk_register_{register_id}.pdf",
                background=lambda: os.unlink(tmp_file_path)  # Clean up temp file
            )
            
    except Exception as e:
        logger.error(f"Error generating report: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/reports/register/{register_id}/summary")
async def get_register_summary(register_id: str):
    """Get summary statistics for a risk register"""
    try:
        register = await risk_register_repository.get_risk_register_by_id(ObjectId(register_id))
        if not register:
            raise HTTPException(status_code=404, detail="Risk register not found")
            
        # Calculate summary statistics
        total_risks = len(register.risks)
        risk_by_impact = {}
        risk_by_likelihood = {}
        risk_by_treatment = {}
        
        for risk in register.risks:
            # Count by impact
            impact = risk.impact.value
            risk_by_impact[impact] = risk_by_impact.get(impact, 0) + 1
            
            # Count by likelihood
            likelihood = risk.likelihood.value
            risk_by_likelihood[likelihood] = risk_by_likelihood.get(likelihood, 0) + 1
            
            # Count by treatment strategy
            treatment = risk.treatment_strategy
            risk_by_treatment[treatment] = risk_by_treatment.get(treatment, 0) + 1
            
        return {
            "register_id": str(register.id),
            "title": register.title,
            "organization": register.organization,
            "total_risks": total_risks,
            "status": register.status,
            "created_at": register.created_at,
            "updated_at": register.updated_at,
            "risk_distribution": {
                "by_impact": risk_by_impact,
                "by_likelihood": risk_by_likelihood,
                "by_treatment_strategy": risk_by_treatment
            }
        }
        
    except Exception as e:
        logger.error(f"Error getting register summary: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")
