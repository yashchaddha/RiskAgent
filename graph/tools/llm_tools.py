"""
LLM tools for the Langraph workflow
"""
import json
import asyncio
import re
from typing import List, Dict, Any
from openai import AsyncOpenAI
from config.settings import settings
from prompts.prompts import RISK_GENERATION_SYSTEM_PROMPT, format_risk_generation_prompt
import logging

logger = logging.getLogger(__name__)

# Initialize OpenAI client
client = AsyncOpenAI(api_key=settings.openai_api_key)

async def call_llm_for_risk_generation(organization_context: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Call LLM to generate risks based on organization context"""
    try:
        # Add randomization elements to ensure different risks each time
        import random
        import time
        
        # Add timestamp and random seed to context for uniqueness
        enhanced_context = organization_context.copy()
        enhanced_context["generation_timestamp"] = str(int(time.time()))
        enhanced_context["random_seed"] = str(random.randint(1000, 9999))
        
        user_prompt = format_risk_generation_prompt(enhanced_context)
        
        # Add instruction for uniqueness in user prompt
        unique_instruction = f"\n\nIMPORTANT: Generate completely UNIQUE risks that are different from standard security checklists. Current timestamp: {enhanced_context['generation_timestamp']}. Be creative and specific to the organization context."
        user_prompt += unique_instruction
        
        logger.info(f"🎲 Generating unique risks with seed: {enhanced_context['random_seed']}")
        
        response = await client.chat.completions.create(
            model=settings.openai_model,
            messages=[
                {"role": "system", "content": RISK_GENERATION_SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.9,  # Increased temperature for more creativity
            max_tokens=4000,  # Increased token limit
            top_p=0.95,  # Add nucleus sampling for more variety
        )
        
        # Parse the JSON response
        content = response.choices[0].message.content.strip()
        logger.info(f"🤖 LLM response content length: {len(content)}")
        logger.info(f"🤖 Raw LLM response preview: {content[:300]}...")
        
        # Try to extract JSON from the response if it's wrapped in markdown
        if content.startswith("```json"):
            content = content.replace("```json", "").replace("```", "").strip()
        elif content.startswith("```"):
            content = content.replace("```", "").strip()
        
        # Additional cleanup for common JSON issues
        content = content.strip()
        if not content.startswith('['):
            # Try to find JSON array in the response
            import re
            json_match = re.search(r'\[.*\]', content, re.DOTALL)
            if json_match:
                content = json_match.group(0)
            else:
                logger.error("No JSON array found in LLM response")
                logger.error(f"Full response: {content}")
                return get_fallback_risks()
        
        try:
            risks_data = json.loads(content)
        except json.JSONDecodeError as e:
            logger.error(f"❌ Failed to parse LLM response as JSON: {e}")
            logger.error(f"❌ Problematic content: {content}")
            # Try one more time with a simpler model
            logger.info("🔄 Retrying with gpt-3.5-turbo...")
            return await call_llm_for_risk_generation_fallback(enhanced_context)
        
        # Validate that we got exactly 10 risks
        if not isinstance(risks_data, list):
            logger.warning(f"❌ Expected list, got {type(risks_data)}")
            return await call_llm_for_risk_generation_fallback(enhanced_context)
            
        if len(risks_data) < 5:
            logger.warning(f"❌ Got only {len(risks_data)} risks, need at least 5")
            return await call_llm_for_risk_generation_fallback(enhanced_context)
        
        # Validate each risk has required fields
        required_fields = ["risk_description", "likelihood", "impact", "treatment_strategy", "treatment_measures"]
        validated_risks = []
        
        for i, risk in enumerate(risks_data):
            if all(field in risk for field in required_fields):
                # Add some validation for field values
                if (risk["likelihood"] in ["Very Low", "Low", "Medium", "High", "Very High"] and
                    risk["impact"] in ["Very Low", "Low", "Medium", "High", "Very High"] and
                    risk["treatment_strategy"] in ["Accept", "Mitigate", "Transfer", "Avoid"]):
                    validated_risks.append(risk)
                    logger.info(f"✅ Validated risk {i+1}: {risk['risk_description'][:50]}...")
                else:
                    logger.warning(f"❌ Invalid field values in risk {i+1}: {risk}")
            else:
                logger.warning(f"❌ Missing required fields in risk {i+1}: {risk}")
        
        if len(validated_risks) < 5:  # Minimum threshold
            logger.warning("❌ Too few valid risks generated, using fallback")
            return get_fallback_risks()
            
        logger.info(f"✅ Successfully generated {len(validated_risks)} unique risks")
        return validated_risks[:10]  # Ensure exactly 10 risks
        
    except Exception as e:
        logger.error(f"❌ Error calling LLM for risk generation: {e}")
        return get_fallback_risks()

async def call_llm_for_risk_generation_fallback(organization_context: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Fallback LLM call with simpler model"""
    try:
        user_prompt = format_risk_generation_prompt(organization_context)
        
        response = await client.chat.completions.create(
            model=settings.openai_model,  # Use simpler, more reliable model
            messages=[
                {"role": "system", "content": "You are a security consultant. Generate exactly 10 unique information security risks in JSON format. Return only valid JSON array."},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.8,
            max_tokens=3000
        )
        
        content = response.choices[0].message.content.strip()
        
        # Clean up the response
        if content.startswith("```json"):
            content = content.replace("```json", "").replace("```", "").strip()
        elif content.startswith("```"):
            content = content.replace("```", "").strip()
            
        risks_data = json.loads(content)
        
        if isinstance(risks_data, list) and len(risks_data) >= 5:
            logger.info(f"✅ Fallback generation successful: {len(risks_data)} risks")
            return risks_data[:10]
        else:
            logger.warning("❌ Fallback also failed, using hardcoded fallback")
            return get_fallback_risks()
            
    except Exception as e:
        logger.error(f"❌ Fallback generation failed: {e}")
        return get_fallback_risks()

async def call_llm_for_intent_parsing(user_message: str) -> str:
    """Call LLM to parse user intent"""
    try:
        system_prompt = """
        You are an intent classifier for a risk assessment chatbot. 
        Analyze the user's message and classify it into one of these intents:
        
        - "greeting": User is greeting or starting conversation
        - "help": User is asking for help or information about ISO 27001, risks, etc.
        - "generate_risks": User wants to generate new risks
        - "review_risks": User wants to review, edit, or select risks. This includes:
          * "Change likelihood of R-001 to High"
          * "Update impact of R-002 to Medium" 
          * "Set treatment_strategy of R-003 to Accept"
          * "Edit risk R-004"
          * "Accept R-001"
          * "Reject R-002"
          * "Select R-003"
          * Any command that modifies risk properties or selection status
        - "finalize_risks": User wants to finalize their risk selection
        - "metadata_input": User is providing metadata (asset value, department, etc.)
        - "generate_report": User wants to generate a report
        - "exit": User wants to end the session
        - "other": Any other intent
        
        IMPORTANT: Any message that contains a risk ID (like R-001, R-002, etc.) and action words
        (change, update, set, edit, modify, accept, reject, select, deselect) should be classified as "review_risks".
        
        Examples:
        - "Change likelihood of R-007 to High" → review_risks
        - "Accept R-001" → review_risks
        - "Reject R-005" → review_risks
        - "Update R-003 impact to Medium" → review_risks
        - "Edit R-002" → review_risks
        
        Return only the intent name, nothing else.
        """
        
        # Pre-check for risk editing patterns to avoid LLM misclassification
        user_message_lower = user_message.lower()
        risk_edit_patterns = [
            r'\b(change|update|set|edit|modify|accept|reject|select|deselect)\b.*\br-\d+\b',
            r'\br-\d+\b.*(likelihood|impact|strategy|description|measures)',
            r'\b(change|update|set)\b.*(likelihood|impact|treatment)',
            r'\b(accept|reject)\b.*\br-\d+\b',
            r'\br-\d+\b.*(accept|reject)',
        ]
        
        for pattern in risk_edit_patterns:
            if re.search(pattern, user_message_lower):
                logger.info(f"🎯 Pre-classified as review_risks based on pattern: {pattern}")
                return "review_risks"
        
        response = await client.chat.completions.create(
            model=settings.openai_model,  # Use faster model for intent parsing
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message}
            ],
            temperature=0.1,
            max_tokens=50
        )
        
        intent = response.choices[0].message.content.strip().lower()
        logger.info(f"🧠 LLM classified intent: {intent}")
        
        # Validate intent
        valid_intents = [
            "greeting", "help", "generate_risks", "review_risks", 
            "finalize_risks", "metadata_input", "generate_report", "exit", "other"
        ]
        
        if intent not in valid_intents:
            return "other"
            
        return intent
        
    except Exception as e:
        logger.error(f"Error parsing intent: {e}")
        return "other"


# new
"""
LLM tools for the Langraph workflow
"""
from prompts.prompts import FAQ_SYSTEM_PROMPT, FAQ_TOPICS, INTENT_CLASSIFICATION_PROMPT

async def generate_risks_llm(organization_context: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Call LLM to generate a list of 10 ISO 27001 risks."""
    try:
        prompt = format_risk_generation_prompt(organization_context)
        response = await client.chat.completions.create(
            model=settings.openai_model,
            messages=[
                {"role": "system", "content": RISK_GENERATION_SYSTEM_PROMPT},
                {"role": "user", "content": prompt}
            ],
            temperature=0.8,
            max_tokens=2000,
        )
        content = response.choices[0].message.content.strip()
        if content.startswith('```'):
            content = re.sub(r'^```.*?\n', '', content)
            content = content.rstrip('```').strip()
        data = json.loads(content)
        if isinstance(data, list):
            return data[:10]
        raise ValueError("LLM did not return a list of risks")
    except Exception as e:
        logger.error(f"Error generating risks: {e}")
        return get_fallback_risks()

async def classify_intent(user_message: str) -> str:
    """Call LLM to classify user intent."""
    try:
        # Quick regex-based pre-check
        # if re.search(r"\br-\d{3}\b.*(change|update|edit|accept|reject)", user_message.lower()):
        #     return "review_risks"
        response = await client.chat.completions.create(
            model=settings.openai_model,
            messages=[
                {"role": "system", "content": INTENT_CLASSIFICATION_PROMPT},
                {"role": "user", "content": user_message}
            ],
            temperature=0.1,
            max_tokens=10,
        )
        intent = response.choices[0].message.content.strip().lower()
        valid = ["greeting","help","generate_risks","review_risks","finalize_risks","metadata_input","generate_report","exit","other"]
        return intent if intent in valid else "other"
    except Exception as e:
        logger.error(f"Error classifying intent: {e}")
        return "other"

async def answer_faq(user_message: str) -> str:
    """Call LLM to answer FAQs about ISO 27001."""
    try:
        response = await client.chat.completions.create(
            model=settings.openai_model,
            messages=[
                {"role": "system", "content": FAQ_SYSTEM_PROMPT},
                {"role": "user", "content": user_message}
            ],
            temperature=0.2,
            max_tokens=500
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        logger.error(f"Error answering FAQ: {e}")
        for topic, answer in FAQ_TOPICS.items():
            if topic in user_message.lower():
                return answer
        return "I'm sorry, I don't have that information right now."

async def parse_risk_command_with_llm(user_message: str) -> Dict[str, Any]:
    """Parse risk edit/selection commands using LLM."""
    try:
        system_prompt = (
            "You are a risk command parser. Extract action, risk_id, field, value. "
            "Return JSON: { action, risk_id, field, value }."
        )
        response = await client.chat.completions.create(
            model=settings.openai_model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message}
            ],
            temperature=0.1,
            max_tokens=100
        )
        text = response.choices[0].message.content.strip()
        return json.loads(text)
    except Exception as e:
        logger.error(f"Error parsing risk command: {e}")
        return {"action": None, "risk_id": None, "field": None, "value": None}

async def call_llm_for_response_generation(context: Dict[str, Any]) -> str:
    """Generate conversational response using LLM."""
    try:
        system_prompt = "You are a helpful ISO 27001 Risk Assessment assistant. Provide clear, friendly responses." 
        user_prompt = f"Context: {json.dumps(context)}"
        response = await client.chat.completions.create(
            model=settings.openai_model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.7,
            max_tokens=500
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        logger.error(f"Error generating response: {e}")
        return "I apologize, I'm having trouble right now."

def get_fallback_risks() -> List[Dict[str, Any]]:
    """Return hardcoded fallback risks with proper RiskValueWeight format."""
    return [
        {"risk_id": "R-001", "risk_description": "Unauthorized physical access to production servers or network closets", "likelihood": {"value": "Medium", "weight": 3}, "impact": {"value": "High", "weight": 4}, "treatment_strategy": "Mitigate", "treatment_measures": ["Install badge readers","CCTV"], "is_approved": False},
        {"risk_id": "R-002", "risk_description": "Theft or loss of mobile devices containing sensitive data", "likelihood": {"value": "High", "weight": 4}, "impact": {"value": "Medium", "weight": 3}, "treatment_strategy": "Mitigate", "treatment_measures": ["Disk encryption","Remote wipe"], "is_approved": False},
        {"risk_id": "R-003", "risk_description": "Malware infection via USB drives or external media", "likelihood": {"value": "Medium", "weight": 3}, "impact": {"value": "High", "weight": 4}, "treatment_strategy": "Mitigate", "treatment_measures": ["Disable autorun","Real-time anti-malware"], "is_approved": False},
        {"risk_id": "R-004", "risk_description": "Phishing attacks leading to credential compromise", "likelihood": {"value": "High", "weight": 4}, "impact": {"value": "High", "weight": 4}, "treatment_strategy": "Mitigate", "treatment_measures": ["Phishing simulations","MFA"], "is_approved": False},
        {"risk_id": "R-005", "risk_description": "Ransomware encrypting production data and demanding payment", "likelihood": {"value": "Medium", "weight": 3}, "impact": {"value": "Very High", "weight": 5}, "treatment_strategy": "Mitigate", "treatment_measures": ["Offline backups","Network segmentation"], "is_approved": False},
        {"risk_id": "R-006", "risk_description": "Insider threat: improper disclosure or sabotage of proprietary processes", "likelihood": {"value": "Low", "weight": 2}, "impact": {"value": "Very High", "weight": 5}, "treatment_strategy": "Mitigate", "treatment_measures": ["Least-privilege","Activity logging"], "is_approved": False},
        {"risk_id": "R-007", "risk_description": "Supplier service‑outage or data breach at vendor", "likelihood": {"value": "Medium", "weight": 3}, "impact": {"value": "High", "weight": 4}, "treatment_strategy": "Transfer", "treatment_measures": ["ISO 27001 SLAs","Audit reviews"], "is_approved": False},
        {"risk_id": "R-008", "risk_description": "Unpatched vulnerabilities in SCADA systems", "likelihood": {"value": "Medium", "weight": 3}, "impact": {"value": "Very High", "weight": 5}, "treatment_strategy": "Mitigate", "treatment_measures": ["OT patch process","Network segmentation"], "is_approved": False},
        {"risk_id": "R-009", "risk_description": "Unintentional data disclosure via misconfigured shares", "likelihood": {"value": "High", "weight": 4}, "impact": {"value": "Medium", "weight": 3}, "treatment_strategy": "Mitigate", "treatment_measures": ["RBAC","DLP"], "is_approved": False},
        {"risk_id": "R-010", "risk_description": "Natural disasters damaging primary data center", "likelihood": {"value": "Low", "weight": 2}, "impact": {"value": "Very High", "weight": 5}, "treatment_strategy": "Transfer", "treatment_measures": ["Off-site DR","Generators"], "is_approved": False},
    ]

async def retry_llm_call(llm_fn, *args, max_retries: int = 3, **kwargs):
    """Retry helper with exponential backoff."""
    for i in range(max_retries):
        try:
            return await llm_fn(*args, **kwargs)
        except Exception as e:
            if i == max_retries - 1:
                raise e
            wait = 2 ** i
            logger.warning(f"Retry {i+1}/{max_retries} after {wait}s: {e}")
            await asyncio.sleep(wait)
