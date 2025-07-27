import logging
from typing import List, Dict, Any
from config.settings import settings
from openai import AsyncOpenAI
import json

logger = logging.getLogger(__name__)

# Initialize OpenAI client
client = AsyncOpenAI(api_key=settings.openai_api_key)

async def generate_risk_summary(approved_risks: List[Dict[str, Any]], organization: str = "Organization") -> Dict[str, str]:
    """Generate an AI-powered risk summary and analysis"""
    
    if not approved_risks:
        return {
            "executive_summary": "No approved risks found for analysis.",
            "key_findings": "No risks to analyze.",
            "recommendations": "Please approve some risks before generating a summary."
        }
    
    try:
        # Prepare risk data for analysis
        risk_summary_data = []
        for risk in approved_risks:
            risk_info = {
                "id": risk.get("risk_id", "Unknown"),
                "description": risk.get("risk_description", ""),
                "likelihood": risk.get("likelihood", {}).get("value", "Unknown"),
                "impact": risk.get("impact", {}).get("value", "Unknown"),
                "score": risk.get("inherent_risk_score", 0),
                "treatment": risk.get("treatment_strategy", "Unknown"),
                "measures": risk.get("treatment_measures", ""),
                "department": risk.get("department", "Not specified"),
                "owner": risk.get("risk_owner", "Not specified")
            }
            risk_summary_data.append(risk_info)
        
        # Calculate some basic statistics
        total_risks = len(approved_risks)
        high_risk_count = len([r for r in approved_risks if r.get('inherent_risk_score', 0) >= 16])
        medium_risk_count = len([r for r in approved_risks if 9 <= r.get('inherent_risk_score', 0) < 16])
        low_risk_count = len([r for r in approved_risks if r.get('inherent_risk_score', 0) < 9])
        
        # Get treatment strategy distribution
        treatment_strategies = {}
        for risk in approved_risks:
            strategy = risk.get('treatment_strategy', 'Unknown')
            treatment_strategies[strategy] = treatment_strategies.get(strategy, 0) + 1
        
        # Create prompt for LLM analysis
        prompt = f"""
Analyze the following risk assessment data for {organization} and provide a comprehensive summary:

RISK STATISTICS:
- Total Risks: {total_risks}
- High Risk (Score ≥16): {high_risk_count}
- Medium Risk (Score 9-15): {medium_risk_count}  
- Low Risk (Score ≤8): {low_risk_count}

TREATMENT STRATEGIES:
{json.dumps(treatment_strategies, indent=2)}

DETAILED RISKS:
{json.dumps(risk_summary_data, indent=2)}

Please provide a comprehensive analysis in the following JSON format:
{{
    "executive_summary": "A 2-3 sentence high-level summary of the organization's risk posture and key findings",
    "key_findings": "Bullet-pointed list of 3-5 key insights about the risk landscape, patterns, and critical areas of concern",
    "recommendations": "Specific, actionable recommendations for risk management prioritization and improvement strategies",
    "risk_profile_analysis": "Analysis of the risk distribution and what it means for the organization",
    "treatment_effectiveness": "Assessment of the chosen treatment strategies and their appropriateness"
}}

Focus on:
1. Overall risk maturity and coverage
2. Risk distribution patterns and hotspots
3. Treatment strategy effectiveness
4. Gaps or areas needing attention
5. Prioritization recommendations

Be professional, actionable, and specific to the provided data.
"""

        # Get AI analysis
        response = await client.chat.completions.create(
            model=settings.openai_model,
            messages=[
                {"role": "system", "content": "You are an expert risk management consultant providing analysis for ISO 27001 compliance. Provide professional, actionable insights based on the risk data."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,
            max_tokens=1500
        )
        
        content = response.choices[0].message.content.strip()
        logger.info(f"🤖 Raw LLM risk summary response: {content[:200]}...")
        
        # Clean up response if it has markdown formatting
        if content.startswith("```json"):
            content = content.replace("```json", "").replace("```", "").strip()
        elif content.startswith("```"):
            content = content.replace("```", "").strip()
        
        # Parse JSON response
        try:
            summary_data = json.loads(content)
            logger.info("✅ Successfully parsed risk summary JSON")
            
            # Ensure all required fields are present
            required_fields = ["executive_summary", "key_findings", "recommendations", "risk_profile_analysis", "treatment_effectiveness"]
            for field in required_fields:
                if field not in summary_data:
                    summary_data[field] = f"Analysis for {field.replace('_', ' ')} not available."
            
            return summary_data
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse LLM response as JSON: {e}. Content: {content[:200]}...")
            # Fallback to basic summary
            return generate_fallback_summary(approved_risks, organization)
            
    except Exception as e:
        logger.error(f"Error generating AI risk summary: {e}")
        # Fallback to basic summary
        return generate_fallback_summary(approved_risks, organization)

def generate_fallback_summary(approved_risks: List[Dict[str, Any]], organization: str) -> Dict[str, str]:
    """Generate a basic fallback summary when AI analysis fails"""
    
    total_risks = len(approved_risks)
    high_risk_count = len([r for r in approved_risks if r.get('inherent_risk_score', 0) >= 16])
    medium_risk_count = len([r for r in approved_risks if 9 <= r.get('inherent_risk_score', 0) < 16])
    low_risk_count = len([r for r in approved_risks if r.get('inherent_risk_score', 0) < 9])
    
    # Most common treatment strategy
    treatment_strategies = {}
    for risk in approved_risks:
        strategy = risk.get('treatment_strategy', 'Unknown')
        treatment_strategies[strategy] = treatment_strategies.get(strategy, 0) + 1
    
    most_common_treatment = max(treatment_strategies.items(), key=lambda x: x[1])[0] if treatment_strategies else "Unknown"
    
    return {
        "executive_summary": f"{organization} has identified {total_risks} risks for management, with {high_risk_count} high-priority risks requiring immediate attention.",
        "key_findings": f"• {high_risk_count} high-risk items need priority treatment\n• {medium_risk_count} medium-risk items require monitoring\n• {low_risk_count} low-risk items are manageable\n• Most common treatment strategy: {most_common_treatment}",
        "recommendations": "• Focus immediate resources on high-risk items\n• Establish regular monitoring for medium-risk items\n• Review treatment strategies for effectiveness\n• Consider risk transfer or acceptance for low-priority items",
        "risk_profile_analysis": f"The organization shows a {'conservative' if high_risk_count < total_risks * 0.3 else 'aggressive'} risk profile with emphasis on {'mitigation' if most_common_treatment == 'Mitigate' else 'varied treatment approaches'}.",
        "treatment_effectiveness": f"Treatment strategies are {'well-distributed' if len(treatment_strategies) > 2 else 'concentrated'}, indicating {'mature' if len(treatment_strategies) > 2 else 'developing'} risk management practices."
    }