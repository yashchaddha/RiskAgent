INTENT_CLASSIFICATION_SYSTEM_PROMPT = """You are an expert at understanding user intents in a risk management context. 

You must classify the user's message into ONE of these intents:

1. **general_question** - Questions about risks, definitions, explanations, how-to guides
   Examples: "What is operational risk?", "How do I assess impact?", "Tell me about risk matrices"

2. **change_matrix** - Requests to modify likelihood/impact matrix size (3x3, 4x4, 5x5)
   Examples: "Change to 4x4 matrix", "Update risk matrix to 4*4", "I want 5x5", "Switch to 3x3", "Can we use a different matrix size?"

3. **generate_risks** - Requests to create/generate new risks for their organization
   Examples: "Generate risks", "Create risks for my company", "I need more risks", "Show me potential risks"

4. **view_risks** - Requests to see existing finalized risks
   Examples: "Show my risks", "What risks do I have?", "Display my finalized risks"

5. **generate_report** - Request to create final risk report
   Examples: "Generate report", "Create risk report", "I want the final report"

Consider the user's current stage context when classifying. Be precise and respond with ONLY the intent name.
"""

def get_intent_classification_prompt(user_message: str, current_stage: str, conversation_context: str = "") -> str:
    """Generate intent classification prompt with context"""
    
    context_info = f"""
Current User Stage: {current_stage}
Recent Conversation Context: {conversation_context}
User Message: "{user_message}"
"""
    
    stage_specific_guidance = ""
    if current_stage == "welcome":
        stage_specific_guidance = "\nNote: User is at welcome stage, likely asking questions or wanting to start risk generation."
    elif current_stage == "risk_generation":
        stage_specific_guidance = "\nNote: User is in risk generation phase, may want to generate more risks or finalize existing ones."
    elif current_stage == "risk_editing":
        stage_specific_guidance = "\nNote: User is reviewing generated risks, may want to generate more or proceed to report generation."
    
    return f"{context_info}{stage_specific_guidance}\n\nClassify the intent:"

# Intent validation patterns
INTENT_PATTERNS = {
    "general_question": [
        "what is", "how do", "explain", "tell me about", "define", "meaning", "example", 
        "best practice", "methodology", "approach", "why", "when", "help me understand"
    ],
    "change_matrix": [
        "change matrix", "4x4", "5x5", "3x3", "4*4", "5*5", "3*3", 
        "matrix size", "different matrix", "update matrix", "modify matrix", 
        "new matrix", "risk matrix", "change to", "update to", "switch to",
        "4 x 4", "5 x 5", "3 x 3", "4 * 4", "5 * 5", "3 * 3"
    ],
    "generate_risks": [
        "generate", "create risks", "new risks", "more risks", "add risks", 
        "risks for", "potential risks", "identify risks"
    ],
    "view_risks": [
        "show risks", "my risks", "current risks", "existing risks", "finalized risks", 
        "display risks", "list risks"
    ],
    "generate_report": [
        "generate report", "create report", "final report", "risk report", 
        "summary report", "export report"
    ]
}

def validate_intent_classification(user_message: str, predicted_intent: str) -> bool:
    """Validate if predicted intent matches message patterns"""
    user_message_lower = user_message.lower()
    patterns = INTENT_PATTERNS.get(predicted_intent, [])
    
    return any(pattern in user_message_lower for pattern in patterns)

"""
Welcome Message Prompts for Risk Management Agent
Contextual welcome messages based on user stage and progress
"""

WELCOME_MESSAGE_SYSTEM_PROMPT = """You are a friendly and professional Risk Management Assistant. Generate personalized welcome messages that:

1. Acknowledge the user's current progress in their risk assessment journey
2. Provide clear guidance on next steps
3. Maintain a helpful and encouraging tone
4. Keep messages concise but informative
5. Always offer to answer questions about risk management

The user journey stages are:
- welcome: First time or early stage
- risk_generation: Generating risks for organization
- risk_editing: Selecting and editing generated risks
- report_ready: Final report has been generated

Be specific about their progress and what they can do next.
"""

def get_welcome_prompt_new_user(user_name: str, organization: str, industry: str) -> str:
    """Welcome message for new users"""
    return f"""
Generate a welcome message for a new user with these details:
- Name: {user_name}
- Organization: {organization}
- Industry: {industry}
- Current Stage: Just registered
- Matrix: Default 3x3 (Low, Medium, High)

Include:
1. Warm welcome to the Risk Management Agent
2. Brief explanation of what they can accomplish
3. Next steps (generate risks for their organization)
4. Mention they can ask questions anytime
5. Note about matrix customization options (3x3, 4x4, 5x5)

Keep it welcoming, professional, and informative.
"""

def get_welcome_prompt_returning_user(user_name: str, organization: str, current_stage: str, 
                                    progress_summary: dict) -> str:
    """Welcome message for returning users"""
    
    progress_text = ""
    if progress_summary.get("finalized_risks_count", 0) > 0:
        progress_text += f"- {progress_summary['finalized_risks_count']} risks finalized\n"
    if progress_summary.get("generated_risks_count", 0) > 0:
        progress_text += f"- {progress_summary['generated_risks_count']} risks generated and available for selection\n"
    if progress_summary.get("reports_count", 0) > 0:
        progress_text += f"- {progress_summary['reports_count']} risk reports created\n"
    
    matrix_info = progress_summary.get("matrix_size", "3x3")
    
    return f"""
Generate a welcome back message for a returning user:
- Name: {user_name}
- Organization: {organization}
- Current Stage: {current_stage}
- Current Matrix: {matrix_info}

Progress Summary:
{progress_text}

Based on their current stage "{current_stage}", provide:
1. Personalized welcome back message
2. Summary of their current progress
3. Clear next steps based on their stage
4. Reminder that they can ask questions anytime
5. Stage-specific guidance

Stage-specific next steps:
- welcome: Start by generating risks for their organization
- risk_generation: Review generated risks or create more
- risk_editing: Complete risk information and generate report
- report_ready: Access their risk report or start new assessment

Keep it encouraging and action-oriented.
"""

def get_progress_summary_context(current_stage: str, finalized_count: int, generated_count: int, reports_count: int) -> str:
    """Generate progress context for welcome messages"""
    
    stage_descriptions = {
        "welcome": "Getting started with risk assessment",
        "risk_generation": "Generating risks for your organization", 
        "risk_editing": "Selecting and refining generated risks",
        "report_ready": "Risk assessment completed"
    }
    
    return f"""
Current Progress:
- Stage: {stage_descriptions.get(current_stage, current_stage)}
- Finalized Risks: {finalized_count}
- Generated Risks Available: {generated_count}
- Reports Created: {reports_count}
"""

# Welcome message templates for quick responses
WELCOME_TEMPLATES = {
    "first_time": """
🎉 Welcome to the Risk Management Agent, {user_name}!

I'm here to help {organization} identify, assess, and manage risks specific to the {industry} industry.

**What we'll accomplish together:**
✓ Generate tailored risks for your organization
✓ Assess likelihood and impact using risk matrices
✓ Develop treatment strategies
✓ Create comprehensive risk reports

**Your current setup:**
- Risk Matrix: 3x3 (Low, Medium, High)
- You can change this to 4x4 or 5x5 anytime

**Ready to start?** Just ask me to "generate risks" for {organization}, or feel free to ask any questions about risk management!

💡 *Tip: You can ask me questions about risk management concepts at any point in our journey.*
""",
    
    "returning_basic": """
👋 Welcome back, {user_name}!

**Your Progress:**
{progress_summary}

**Next Steps:** {next_steps}

Need help or have questions? Just ask! I'm here to guide you through your risk assessment journey.
""",
    
    "ready_for_report": """
🎯 Excellent progress, {user_name}!

You've completed the risk assessment for {organization}. Your finalized risks are ready, and we can now generate your comprehensive risk report.

**What's included in your report:**
- Executive summary of identified risks
- Risk matrix visualization  
- Treatment strategies and measures
- Risk register with all details

Would you like me to generate your final risk report now?
"""
}

def get_quick_welcome_message(template_type: str, **kwargs) -> str:
    """Get pre-formatted welcome message"""
    template = WELCOME_TEMPLATES.get(template_type, WELCOME_TEMPLATES["returning_basic"])
    return template.format(**kwargs)

"""
Risk Generation Prompts for Risk Management Agent
Generate contextual risks based on organization and industry
"""

RISK_GENERATION_SYSTEM_PROMPT = """You are an expert risk management consultant with deep knowledge across all industries. Generate realistic, specific, and actionable risks for organizations.

Your task is to create exactly 10 risks that are:
1. **Relevant** to the specific organization and industry
2. **Specific** rather than generic
3. **Actionable** with clear treatment strategies
4. **Realistic** based on current business environment
5. **Varied** across different risk categories (operational, financial, strategic, compliance, technology, etc.)

For each risk, provide:
- **description**: Clear, specific description (50-200 words)
- **impact**: Level from the provided impact scale
- **likelihood**: Level from the provided likelihood scale  
- **treatment_strategy**: High-level approach (Accept, Avoid, Mitigate, Transfer)
- **treatment_measures**: Specific actionable measures as a SINGLE STRING (format: "1. First measure 2. Second measure 3. Third measure" - NOT an array)

Important: 
- Only use the exact impact and likelihood values provided in the scales. Do not invent new levels.
- treatment_measures must be a string, not an array or list

Format your response as a valid JSON array of risk objects.
"""

def get_risk_generation_prompt(organization: str, industry: str, likelihood_scale: list, 
                             impact_scale: list, additional_context: str = "") -> str:
    """Generate risk generation prompt with organization context"""
    
    industry_specific_guidance = get_industry_risk_guidance(industry)
    
    prompt = f"""
Generate exactly 10 specific risks for this organization:

**Organization:** {organization}
**Industry:** {industry}
**Additional Context:** {additional_context}

**Available Scales:**
- Likelihood Scale: {likelihood_scale}
- Impact Scale: {impact_scale}

**Industry-Specific Considerations:**
{industry_specific_guidance}

**Risk Categories to Consider:**
- Operational risks (day-to-day operations, supply chain, human resources)
- Financial risks (cash flow, credit, market volatility, compliance costs)
- Strategic risks (competition, market changes, technology disruption)
- Compliance/Regulatory risks (legal requirements, industry regulations)
- Technology risks (cybersecurity, system failures, data breaches)
- Reputation risks (public relations, customer satisfaction, brand damage)
- Environmental risks (climate change, sustainability, resource scarcity)

**Requirements:**
1. Each risk must be specific to {organization} in the {industry} industry
2. Use only the provided likelihood and impact scale values
3. Include realistic treatment strategies and specific measures
4. Vary risk types across different categories
5. Consider current business environment and trends

Format as JSON array:
[
  {{
    "description": "Specific risk description...",
    "impact": "High",
    "likelihood": "Medium", 
    "treatment_strategy": "Mitigate",
    "treatment_measures": "1. Specific action 2. Another action 3. Third action"
  }},
  ...
]
"""
    
    return prompt

def get_industry_risk_guidance(industry: str) -> str:
    """Get industry-specific risk guidance"""
    
    industry_guidance = {
        "Technology": """
        - Cybersecurity threats and data breaches
        - Software vulnerabilities and system downtime
        - Talent acquisition and retention challenges
        - Rapid technology obsolescence
        - Regulatory compliance (data privacy, AI ethics)
        - Intellectual property theft
        - Cloud infrastructure dependencies
        """,
        
        "Healthcare": """
        - Patient safety and medical errors
        - Regulatory compliance (HIPAA, FDA)
        - Cybersecurity and patient data protection
        - Medical equipment failures
        - Staff shortages and burnout
        - Insurance and liability issues
        - Pharmaceutical supply chain disruptions
        """,
        
        "Financial Services": """
        - Credit and market risks
        - Regulatory compliance (Basel III, Dodd-Frank)
        - Cybersecurity and fraud
        - Interest rate fluctuations
        - Liquidity risks
        - Operational failures
        - Reputation and trust issues
        """,
        
        "Manufacturing": """
        - Supply chain disruptions
        - Equipment breakdowns and maintenance
        - Quality control and product defects
        - Workplace safety and accidents
        - Environmental compliance
        - Raw material price volatility
        - Trade and tariff impacts
        """,
        
        "Retail": """
        - Consumer demand fluctuations
        - Supply chain and inventory management
        - E-commerce and digital transformation
        - Seasonal sales variations
        - Competition and market saturation
        - Customer data security
        - Economic downturns impact
        """,
        
        "Education": """
        - Student safety and security
        - Technology infrastructure and digital divide
        - Regulatory compliance and accreditation
        - Funding and budget constraints
        - Staff recruitment and retention
        - Reputation and enrollment impacts
        - Health and pandemic responses
        """,
        
        "Government": """
        - Public safety and emergency response
        - Cybersecurity and critical infrastructure
        - Budget constraints and fiscal management
        - Regulatory compliance and legal challenges
        - Public trust and transparency
        - Political and policy changes
        - Service delivery disruptions
        """,
        
        "Energy": """
        - Environmental and safety incidents
        - Regulatory and policy changes
        - Price volatility and market fluctuations
        - Infrastructure aging and maintenance
        - Climate change and extreme weather
        - Technology transition and renewable energy
        - Supply chain and geopolitical risks
        """
    }
    
    return industry_guidance.get(industry, """
        - Operational disruptions and process failures
        - Market competition and economic downturns
        - Regulatory compliance and legal issues
        - Technology failures and cybersecurity threats
        - Human resources and talent management
        - Financial risks and cash flow issues
        - Reputation and customer satisfaction risks
        """)

def get_additional_risk_generation_prompt(organization: str, industry: str, likelihood_scale: list, 
                                        impact_scale: list, existing_risks_count: int) -> str:
    """Generate prompt for additional risks when user asks for more"""
    
    return f"""
Generate 10 additional risks for {organization} (Industry: {industry}).

**Context:** 
- Organization already has {existing_risks_count} risks identified
- Focus on different risk areas than previously covered
- Maintain high quality and specificity

**Scales:**
- Likelihood: {likelihood_scale}
- Impact: {impact_scale}

**Focus Areas for Additional Risks:**
- Emerging risks and future challenges
- Cross-functional risks spanning multiple departments
- External risks from market and environment
- Strategic and long-term risks
- Risks specific to business model and operations

Ensure these risks complement existing ones and provide comprehensive coverage.

Format as JSON array with same structure as before.
"""

# Risk validation patterns
RISK_VALIDATION_PATTERNS = {
    "required_fields": ["description", "impact", "likelihood", "treatment_strategy", "treatment_measures"],
    "treatment_strategies": ["Accept", "Avoid", "Mitigate", "Transfer"],
    "min_description_length": 20,
    "max_description_length": 500
}

def validate_generated_risk(risk_data: dict, allowed_impact: list, allowed_likelihood: list) -> bool:
    """Validate generated risk data"""
    required_fields = RISK_VALIDATION_PATTERNS["required_fields"]
    
    # Check required fields
    if not all(field in risk_data for field in required_fields):
        return False
    
    # Check impact and likelihood values
    if risk_data["impact"] not in allowed_impact:
        return False
    if risk_data["likelihood"] not in allowed_likelihood:
        return False
    
    # Check treatment strategy
    if risk_data["treatment_strategy"] not in RISK_VALIDATION_PATTERNS["treatment_strategies"]:
        return False
    
    # Check description length
    desc_len = len(risk_data["description"])
    if desc_len < RISK_VALIDATION_PATTERNS["min_description_length"] or \
       desc_len > RISK_VALIDATION_PATTERNS["max_description_length"]:
        return False
    
    # Check that treatment_measures is a string, not an array
    if not isinstance(risk_data["treatment_measures"], str):
        return False
    
    return True

"""
General Q&A Prompts for Risk Management Agent
Contextual responses to user questions throughout their journey
"""

GENERAL_QA_SYSTEM_PROMPT = """You are an expert Risk Management consultant and helpful assistant. Answer user questions about risk management with:

1. **Accurate Information**: Provide correct, up-to-date risk management knowledge
2. **Contextual Relevance**: Consider the user's organization, industry, and current stage
3. **Practical Guidance**: Give actionable advice and real-world examples
4. **Clear Communication**: Use clear, professional language appropriate for business users
5. **Encouraging Tone**: Be supportive and help users progress in their risk journey

You have deep expertise in:
- Risk identification, assessment, and treatment
- Risk matrices and scoring methodologies  
- Industry-specific risk considerations
- Risk management frameworks (ISO 31000, COSO, etc.)
- Business continuity and crisis management
- Regulatory compliance across industries

Always relate your answers to the user's specific context when possible.
"""

def get_general_qa_prompt(user_question: str, user_context: dict) -> str:
    """Generate contextual Q&A prompt"""
    
    context_info = f"""
User Context:
- Organization: {user_context.get('organization', 'Not specified')}
- Industry: {user_context.get('industry', 'Not specified')}
- Current Stage: {user_context.get('current_stage', 'welcome')}
- Matrix Size: {user_context.get('matrix_size', '3x3')}
- Finalized Risks: {user_context.get('finalized_risks_count', 0)}
- Generated Risks: {user_context.get('generated_risks_count', 0)}

User Question: "{user_question}"
"""
    
    stage_context = get_stage_specific_guidance(user_context.get('current_stage', 'welcome'))
    industry_context = get_industry_context_for_qa(user_context.get('industry', ''))
    
    return f"""
{context_info}

{stage_context}

{industry_context}

Provide a helpful, informative answer that:
1. Directly addresses their question
2. Considers their organizational and industry context
3. Relates to their current stage in the risk assessment process
4. Includes practical examples when relevant
5. Encourages them to continue their risk management journey

Keep your response professional, clear, and actionable.
"""

def get_stage_specific_guidance(current_stage: str) -> str:
    """Get guidance specific to user's current stage"""
    
    stage_guidance = {
        "welcome": """
Stage Context: User is at the beginning of their risk assessment journey.
- They may have questions about getting started
- Focus on explaining fundamentals and building confidence
- Guide them toward risk generation when appropriate
""",
        
        "risk_generation": """
Stage Context: User is in the risk generation phase.
- They may have questions about the generated risks
- Help them understand risk categories and assessment
- Guide them on risk selection and customization
""",
        
        "risk_editing": """
Stage Context: User is selecting and editing generated risks.
- They may need help with risk assessment criteria
- Explain likelihood and impact evaluation
- Help them refine risk descriptions and treatments
""",
        
        "data_collection": """
Stage Context: User is adding detailed information to finalized risks.
- They may need clarification on additional data fields
- Help them understand asset values, departments, ownership
- Guide them on setting realistic target dates and progress tracking
""",
        
        
        "report_ready": """
Stage Context: User has completed their risk assessment.
- They may have questions about interpreting the report
- Help them understand next steps for risk management
- Guide them on ongoing risk monitoring and updates
"""
    }
    
    return stage_guidance.get(current_stage, "")

def get_industry_context_for_qa(industry: str) -> str:
    """Get industry-specific context for Q&A responses"""
    
    if not industry or industry == "Not specified":
        return ""
    
    industry_contexts = {
        "Technology": """
Industry Context: Technology sector considerations:
- Focus on cybersecurity, data privacy, and system reliability
- Consider rapid technology changes and innovation risks
- Address talent acquisition and intellectual property concerns
""",
        
        "Healthcare": """
Industry Context: Healthcare sector considerations:
- Emphasize patient safety and regulatory compliance
- Consider medical device reliability and data security
- Address staffing challenges and liability issues
""",
        
        "Financial Services": """
Industry Context: Financial services considerations:
- Focus on regulatory compliance and market risks
- Consider credit risks and operational failures
- Address cybersecurity and reputation management
""",
        
        "Manufacturing": """
Industry Context: Manufacturing considerations:
- Emphasize supply chain and operational risks
- Consider equipment reliability and safety
- Address quality control and environmental compliance
""",
        
        "Retail": """
Industry Context: Retail sector considerations:
- Focus on customer experience and market competition
- Consider supply chain and inventory management
- Address digital transformation and data security
""",
        
        "Education": """
Industry Context: Education sector considerations:
- Emphasize student and staff safety
- Consider technology infrastructure and accessibility
- Address funding challenges and regulatory compliance
""",
        
        "Government": """
Industry Context: Government sector considerations:
- Focus on public service delivery and transparency
- Consider cybersecurity and infrastructure protection
- Address budget constraints and regulatory compliance
""",
        
        "Energy": """
Industry Context: Energy sector considerations:
- Emphasize safety and environmental protection
- Consider regulatory changes and market volatility
- Address infrastructure reliability and climate risks
"""
    }
    
    return industry_contexts.get(industry, "")

# Common Q&A topics and guidance
COMMON_QA_TOPICS = {
    "risk_definition": """
Risk is the potential for loss, damage, or negative impact due to uncertain events or conditions.
It's typically measured by likelihood (probability) and impact (consequences).
""",
    
    "risk_matrix": """
A risk matrix is a tool that combines likelihood and impact to prioritize risks.
Common sizes are 3x3, 4x4, and 5x5, with different granularity levels.
""",
    
    "risk_treatment": """
The four main risk treatment strategies are:
- Accept: Acknowledge the risk and take no action
- Avoid: Eliminate the risk source or activity
- Mitigate: Reduce likelihood or impact
- Transfer: Share the risk with others (insurance, contracts)
""",
    
    "likelihood_assessment": """
Likelihood assessment considers:
- Historical data and trends
- Expert judgment and experience
- Current controls and safeguards
- External factors and environment
""",
    
    "impact_assessment": """
Impact assessment considers:
- Financial consequences
- Operational disruption
- Reputation damage
- Regulatory implications
- Safety and security effects
"""
}

def get_topic_specific_response(topic: str, user_context: dict) -> str:
    """Get pre-defined response for common topics"""
    base_response = COMMON_QA_TOPICS.get(topic, "")
    
    if not base_response:
        return ""
    
    # Add context-specific examples
    organization = user_context.get('organization', 'your organization')
    industry = user_context.get('industry', 'your industry')
    
    contextualized = f"{base_response}\n\nFor {organization} in the {industry} sector, this means..."
    
    return contextualized


"""
Matrix Update and Report Generation Prompts
"""

# Matrix Update Prompts
MATRIX_UPDATE_SYSTEM_PROMPT = """You are a helpful risk management assistant. Help users understand and update their risk matrix configurations.

Explain the differences between matrix sizes and confirm their choice. Be clear about the implications of changing matrix sizes.
"""

def get_matrix_update_prompt(current_matrix: str, requested_matrix: str, 
                           current_scales: dict, new_scales: dict) -> str:
    """Generate matrix update confirmation prompt"""
    
    return f"""
The user wants to change their risk matrix from {current_matrix} to {requested_matrix}.

Current Configuration:
- Matrix Size: {current_matrix}
- Likelihood Scale: {current_scales['likelihood_scale']}
- Impact Scale: {current_scales['impact_scale']}

New Configuration:
- Matrix Size: {requested_matrix}
- Likelihood Scale: {new_scales['likelihood_scale']}
- Impact Scale: {new_scales['impact_scale']}

Generate a response that:
1. Confirms the matrix change
2. Explains the difference in granularity
3. Notes that existing risks will keep their current values
4. Explains that new risks will use the updated scales
5. Asks for confirmation if needed

Be helpful and informative about the benefits of different matrix sizes.
"""

def get_matrix_explanation_prompt(matrix_size: str) -> str:
    """Explain specific matrix size benefits"""
    
    explanations = {
        "3x3": """
The 3x3 matrix uses simple Low-Medium-High scales:
- **Benefits**: Simple to use, quick assessments, clear categories
- **Best for**: Small organizations, straightforward risk profiles
- **Scales**: Low, Medium, High for both likelihood and impact
""",
        
        "4x4": """
The 4x4 matrix adds "Very Low" for more granularity:
- **Benefits**: Better differentiation, more precise assessments
- **Best for**: Medium organizations, moderate complexity
- **Scales**: Very Low, Low, Medium, High for both dimensions
""",
        
        "5x5": """
The 5x5 matrix offers maximum granularity with "Very High":
- **Benefits**: Most precise assessments, detailed prioritization
- **Best for**: Large organizations, complex risk profiles
- **Scales**: Very Low, Low, Medium, High, Very High for both dimensions
"""
    }
    
    return f"Explain the {matrix_size} risk matrix:\n{explanations.get(matrix_size, '')}"

# Report Generation Prompts
REPORT_GENERATION_SYSTEM_PROMPT = """You are an expert risk management consultant creating executive-level risk reports. 

Generate comprehensive, professional risk reports that provide:
1. Executive summary with key insights
2. Risk landscape overview
3. Detailed risk analysis
4. Treatment recommendations
5. Implementation priorities

Use clear, professional language suitable for senior management and stakeholders.
"""

def get_report_generation_prompt(user_data: dict, finalized_risks: list) -> str:
    """Generate comprehensive risk report prompt"""
    
    organization = user_data.get('organization', 'Organization')
    industry = user_data.get('industry', 'Industry')
    matrix_size = user_data.get('matrix_size', '3x3')
    likelihood_scale = user_data.get('likelihood_scale', ['Low', 'Medium', 'High'])
    impact_scale = user_data.get('impact_scale', ['Low', 'Medium', 'High'])
    
    # Analyze risk distribution
    risk_analysis = analyze_risk_distribution(finalized_risks, likelihood_scale, impact_scale)
    
    return f"""
Generate a comprehensive risk management report for {organization} in the {industry} industry.

**Organization Details:**
- Organization: {organization}
- Industry: {industry}
- Assessment Date: {user_data.get('assessment_date', 'Current')}
- Matrix Used: {matrix_size} ({likelihood_scale} x {impact_scale})

**Risk Summary:**
- Total Risks Assessed: {len(finalized_risks)}
- High Priority Risks: {risk_analysis['high_priority_count']}
- Medium Priority Risks: {risk_analysis['medium_priority_count']}
- Low Priority Risks: {risk_analysis['low_priority_count']}

**Risk Distribution:**
{risk_analysis['distribution_summary']}

**Finalized Risks:**
{format_risks_for_report(finalized_risks)}

**Report Structure Required:**
1. **Executive Summary** (2-3 paragraphs)
   - Key risk insights and overall assessment
   - Critical risks requiring immediate attention
   - Strategic recommendations

2. **Risk Landscape Overview** 
   - Industry-specific context
   - Risk environment analysis
   - Emerging threats and opportunities

3. **Detailed Risk Analysis**
   - Risk categorization and prioritization
   - Risk interdependencies
   - Control effectiveness assessment

4. **Treatment Recommendations**
   - Priority action items
   - Resource allocation guidance
   - Timeline recommendations

5. **Implementation Roadmap**
   - Short-term priorities (0-3 months)
   - Medium-term initiatives (3-12 months)
   - Long-term strategic actions (1+ years)

6. **Risk Register Summary**
   - Tabular summary of all risks
   - Risk owners and target dates
   - Progress tracking framework

**Tone:** Professional, executive-level, actionable
**Length:** Comprehensive but concise (aim for 1500-2000 words)
**Focus:** Strategic insights and practical recommendations
"""

def analyze_risk_distribution(risks: list, likelihood_scale: list, impact_scale: list) -> dict:
    """Analyze risk distribution for report context"""
    
    if not risks:
        return {
            'high_priority_count': 0,
            'medium_priority_count': 0,
            'low_priority_count': 0,
            'distribution_summary': 'No risks to analyze'
        }
    
    # Simple priority calculation based on scale position
    high_priority = 0
    medium_priority = 0
    low_priority = 0
    
    high_likelihood = likelihood_scale[-2:] if len(likelihood_scale) > 2 else [likelihood_scale[-1]]
    high_impact = impact_scale[-2:] if len(impact_scale) > 2 else [impact_scale[-1]]
    
    for risk in risks:
        likelihood = risk.get('likelihood', '')
        impact = risk.get('impact', '')
        
        if likelihood in high_likelihood and impact in high_impact:
            high_priority += 1
        elif likelihood in likelihood_scale[:2] and impact in impact_scale[:2]:
            low_priority += 1
        else:
            medium_priority += 1
    
    distribution_summary = f"""
- High Priority: {high_priority} risks requiring immediate attention
- Medium Priority: {medium_priority} risks for planned mitigation
- Low Priority: {low_priority} risks for monitoring
"""
    
    return {
        'high_priority_count': high_priority,
        'medium_priority_count': medium_priority,
        'low_priority_count': low_priority,
        'distribution_summary': distribution_summary
    }

def format_risks_for_report(risks: list) -> str:
    """Format risks for inclusion in report prompt"""
    
    if not risks:
        return "No finalized risks available"
    
    formatted_risks = []
    for i, risk in enumerate(risks, 1):
        risk_text = f"""
Risk {i}: {risk.get('description', 'No description')}
- Impact: {risk.get('impact', 'Not specified')}
- Likelihood: {risk.get('likelihood', 'Not specified')}
- Treatment Strategy: {risk.get('treatment_strategy', 'Not specified')}
- Treatment Measures: {risk.get('treatment_measures', 'Not specified')}
- Department: {risk.get('department', 'Not specified')}
- Risk Owner: {risk.get('risk_owner', 'Not specified')}
- Target Date: {risk.get('target_date', 'Not specified')}
"""
        formatted_risks.append(risk_text)
    
    return '\n'.join(formatted_risks)


