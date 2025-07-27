from typing import Union, Dict, Any, List
from models.risk_model import RiskRegister
from jinja2 import Template
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

async def generate_report(risk_register: RiskRegister, format: str = "html") -> Union[str, bytes]:
    """Generate a report for the risk register"""
    try:
        if format == "html":
            return await generate_html_report(risk_register)
        elif format == "pdf":
            return await generate_pdf_report(risk_register)
        else:
            raise ValueError(f"Unsupported format: {format}")
            
    except Exception as e:
        logger.error(f"Error generating report: {e}")
        raise

async def generate_report_from_risks(report_data: Dict[str, Any], format: str = "html") -> Union[str, bytes]:
    """Generate a report from risk data (used when working with graph state risks)"""
    try:
        if format == "html":
            return await generate_html_report_from_data(report_data)
        elif format == "pdf":
            return await generate_pdf_report_from_data(report_data)
        else:
            raise ValueError(f"Unsupported format: {format}")
            
    except Exception as e:
        logger.error(f"Error generating report from risk data: {e}")
        raise

async def generate_html_report(risk_register: RiskRegister) -> str:
    """Generate HTML report"""
    try:
        html_template = """
<!DOCTYPE html>
<html>
<head>
    <title>Risk Assessment Report - {{ register.title }}</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 40px; }
        .header { text-align: center; margin-bottom: 30px; }
        .metadata { background: #f5f5f5; padding: 20px; margin-bottom: 30px; }
        .risk-table { width: 100%; border-collapse: collapse; margin-bottom: 30px; }
        .risk-table th, .risk-table td { border: 1px solid #ddd; padding: 12px; text-align: left; }
        .risk-table th { background-color: #4CAF50; color: white; }
        .risk-table tr:nth-child(even) { background-color: #f2f2f2; }
        .summary { background: #e7f3ff; padding: 20px; margin-top: 30px; }
        .high-risk { background-color: #ffebee; }
        .medium-risk { background-color: #fff3e0; }
        .low-risk { background-color: #e8f5e8; }
    </style>
</head>
<body>
    <div class="header">
        <h1>ISO 27001 Risk Assessment Report</h1>
        <h2>{{ register.title }}</h2>
        <h3>{{ register.organization }}</h3>
    </div>
    
    <div class="metadata">
        <h3>Report Metadata</h3>
        <p><strong>Created by:</strong> {{ register.created_by.name }}</p>
        <p><strong>Created date:</strong> {{ register.created_at.strftime('%Y-%m-%d %H:%M') }}</p>
        <p><strong>Last updated:</strong> {{ register.updated_at.strftime('%Y-%m-%d %H:%M') }}</p>
        <p><strong>Status:</strong> {{ register.status }}</p>
        <p><strong>Total risks:</strong> {{ register.total_risks }}</p>
        <p><strong>Report generated:</strong> {{ current_time.strftime('%Y-%m-%d %H:%M') }}</p>
    </div>

    <h3>Risk Register</h3>
    <table class="risk-table">
        <thead>
            <tr>
                <th>Risk ID</th>
                <th>Risk Description</th>
                <th>Likelihood</th>
                <th>Impact</th>
                <th>Risk Score</th>
                <th>Treatment Strategy</th>
                <th>Treatment Measures</th>
                <th>Department</th>
                <th>Risk Owner</th>
                <th>Target Date</th>
                <th>Progress</th>
            </tr>
        </thead>
        <tbody>
            {% for risk in register.risks %}
            <tr class="{% if risk.inherent_risk_score >= 16 %}high-risk{% elif risk.inherent_risk_score >= 9 %}medium-risk{% else %}low-risk{% endif %}">
                <td>{{ risk.risk_id }}</td>
                <td>{{ risk.risk_description }}</td>
                <td>{{ risk.likelihood.value }} ({{ risk.likelihood.weight }})</td>
                <td>{{ risk.impact.value }} ({{ risk.impact.weight }})</td>
                <td>{{ risk.inherent_risk_score }}</td>
                <td>{{ risk.treatment_strategy }}</td>
                <td>{{ risk.treatment_measures }}</td>
                <td>{{ risk.department or 'Not specified' }}</td>
                <td>{{ risk.risk_owner or 'Not specified' }}</td>
                <td>{{ risk.target_date.strftime('%Y-%m-%d') if risk.target_date else 'Not specified' }}</td>
                <td>{{ risk.risk_progress or 'Not started' }}</td>
            </tr>
            {% endfor %}
        </tbody>
    </table>

    <div class="summary">
        <h3>Risk Summary</h3>
        <p><strong>High Risk (Score ≥ 16):</strong> {{ high_risk_count }} risks</p>
        <p><strong>Medium Risk (Score 9-15):</strong> {{ medium_risk_count }} risks</p>
        <p><strong>Low Risk (Score ≤ 8):</strong> {{ low_risk_count }} risks</p>
        
        <h4>Risk Distribution by Treatment Strategy</h4>
        {% for strategy, count in treatment_distribution.items() %}
        <p><strong>{{ strategy }}:</strong> {{ count }} risks</p>
        {% endfor %}
    </div>
</body>
</html>
        """
        
        # Calculate summary statistics
        high_risk_count = len([r for r in risk_register.risks if r.inherent_risk_score >= 16])
        medium_risk_count = len([r for r in risk_register.risks if 9 <= r.inherent_risk_score < 16])
        low_risk_count = len([r for r in risk_register.risks if r.inherent_risk_score < 9])
        
        treatment_distribution = {}
        for risk in risk_register.risks:
            strategy = risk.treatment_strategy
            treatment_distribution[strategy] = treatment_distribution.get(strategy, 0) + 1
        
        template = Template(html_template)
        html_content = template.render(
            register=risk_register,
            current_time=datetime.utcnow(),
            high_risk_count=high_risk_count,
            medium_risk_count=medium_risk_count,
            low_risk_count=low_risk_count,
            treatment_distribution=treatment_distribution
        )
        
        return html_content
        
    except Exception as e:
        logger.error(f"Error generating HTML report: {e}")
        raise

async def generate_html_report_from_data(report_data: Dict[str, Any]) -> str:
    """Generate HTML report from risk data dictionary"""
    try:
        html_template = """
<!DOCTYPE html>
<html>
<head>
    <title>Risk Assessment Report - {{ title }}</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 40px; line-height: 1.6; }
        .header { text-align: center; margin-bottom: 30px; }
        .metadata { background: #f5f5f5; padding: 20px; margin-bottom: 30px; border-radius: 8px; }
        
        /* AI Summary Styles */
        .ai-summary-section { 
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
            color: white; 
            padding: 30px; 
            margin: 30px 0; 
            border-radius: 12px; 
            box-shadow: 0 4px 15px rgba(0,0,0,0.1);
        }
        .ai-summary-section h3 { 
            margin-top: 0; 
            font-size: 24px; 
            text-align: center; 
            margin-bottom: 25px;
        }
        .summary-card { 
            background: rgba(255,255,255,0.95); 
            color: #333; 
            padding: 20px; 
            margin: 15px 0; 
            border-radius: 8px; 
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        }
        .summary-card h4 { 
            margin-top: 0; 
            color: #4CAF50; 
            font-size: 18px; 
            border-bottom: 2px solid #4CAF50; 
            padding-bottom: 8px;
        }
        .summary-grid { 
            display: grid; 
            grid-template-columns: 1fr 1fr; 
            gap: 15px; 
        }
        .findings-content, .recommendations-content { 
            font-size: 14px; 
            line-height: 1.8;
        }
        .executive-summary { 
            background: rgba(76, 175, 80, 0.1); 
            border-left: 4px solid #4CAF50;
        }
        .recommendations { 
            background: rgba(255, 193, 7, 0.1); 
            border-left: 4px solid #FFC107;
        }
        
        /* Table Styles */
        .risk-table { width: 100%; border-collapse: collapse; margin-bottom: 30px; }
        .risk-table th, .risk-table td { border: 1px solid #ddd; padding: 12px; text-align: left; }
        .risk-table th { background-color: #4CAF50; color: white; }
        .risk-table tr:nth-child(even) { background-color: #f2f2f2; }
        .summary { background: #e7f3ff; padding: 20px; margin-top: 30px; border-radius: 8px; }
        .high-risk { background-color: #ffebee; }
        .medium-risk { background-color: #fff3e0; }
        .low-risk { background-color: #e8f5e8; }
        
        /* Responsive */
        @media (max-width: 768px) {
            .summary-grid { grid-template-columns: 1fr; }
            body { margin: 20px; }
        }
    </style>
</head>
<body>
    <div class="header">
        <h1>ISO 27001 Risk Assessment Report</h1>
        <h2>{{ title }}</h2>
        <h3>{{ organization }}</h3>
    </div>
    
    <div class="metadata">
        <h3>Report Metadata</h3>
        <p><strong>Created by:</strong> {{ created_by.name }}</p>
        <p><strong>Created date:</strong> {{ created_at.strftime('%Y-%m-%d %H:%M') }}</p>
        <p><strong>Status:</strong> {{ status }}</p>
        <p><strong>Total risks:</strong> {{ total_risks }}</p>
        <p><strong>Report generated:</strong> {{ current_time.strftime('%Y-%m-%d %H:%M') }}</p>
    </div>

    {% if ai_summary %}
    <div class="ai-summary-section">
        <h3>🤖 AI-Powered Risk Analysis</h3>
        
        <div class="summary-card executive-summary">
            <h4>📊 Executive Summary</h4>
            <p>{{ ai_summary.executive_summary }}</p>
        </div>

        <div class="summary-card key-findings">
            <h4>🔍 Key Findings</h4>
            <div class="findings-content">{{ ai_summary.key_findings|replace('\n', '<br>')|safe }}</div>
        </div>

        <div class="summary-grid">
            <div class="summary-card risk-profile">
                <h4>📈 Risk Profile Analysis</h4>
                <p>{{ ai_summary.risk_profile_analysis }}</p>
            </div>

            <div class="summary-card treatment-analysis">
                <h4>🛡️ Treatment Effectiveness</h4>
                <p>{{ ai_summary.treatment_effectiveness }}</p>
            </div>
        </div>

        <div class="summary-card recommendations">
            <h4>💡 Recommendations</h4>
            <div class="recommendations-content">{{ ai_summary.recommendations|replace('\n', '<br>')|safe }}</div>
        </div>
    </div>
    {% endif %}

    <h3>Risk Register</h3>
    <table class="risk-table">
        <thead>
            <tr>
                <th>Risk ID</th>
                <th>Risk Description</th>
                <th>Likelihood</th>
                <th>Impact</th>
                <th>Risk Score</th>
                <th>Treatment Strategy</th>
                <th>Treatment Measures</th>
                <th>Department</th>
                <th>Risk Owner</th>
                <th>Target Date</th>
                <th>Progress</th>
            </tr>
        </thead>
        <tbody>
            {% for risk in risks %}
            <tr class="{% if risk.get('inherent_risk_score', 0) >= 16 %}high-risk{% elif risk.get('inherent_risk_score', 0) >= 9 %}medium-risk{% else %}low-risk{% endif %}">
                <td>{{ risk.get('risk_id', 'N/A') }}</td>
                <td>{{ risk.get('risk_description', 'N/A') }}</td>
                <td>{{ risk.get('likelihood', {}).get('value', 'N/A') }} ({{ risk.get('likelihood', {}).get('weight', 'N/A') }})</td>
                <td>{{ risk.get('impact', {}).get('value', 'N/A') }} ({{ risk.get('impact', {}).get('weight', 'N/A') }})</td>
                <td>{{ risk.get('inherent_risk_score', 'N/A') }}</td>
                <td>{{ risk.get('treatment_strategy', 'N/A') }}</td>
                <td>{{ risk.get('treatment_measures', 'N/A') }}</td>
                <td>{{ risk.get('department', 'Not specified') }}</td>
                <td>{{ risk.get('risk_owner', 'Not specified') }}</td>
                <td>{{ risk.get('target_date').strftime('%Y-%m-%d') if risk.get('target_date') and hasattr(risk.get('target_date'), 'strftime') else 'Not specified' }}</td>
                <td>{{ risk.get('risk_progress', 'Not started') }}</td>
            </tr>
            {% endfor %}
        </tbody>
    </table>

    <div class="summary">
        <h3>Risk Summary</h3>
        <p><strong>High Risk (Score ≥ 16):</strong> {{ high_risk_count }} risks</p>
        <p><strong>Medium Risk (Score 9-15):</strong> {{ medium_risk_count }} risks</p>
        <p><strong>Low Risk (Score ≤ 8):</strong> {{ low_risk_count }} risks</p>
        
        <h4>Risk Distribution by Treatment Strategy</h4>
        {% for strategy, count in treatment_distribution.items() %}
        <p><strong>{{ strategy }}:</strong> {{ count }} risks</p>
        {% endfor %}
    </div>
</body>
</html>
        """
        
        # Calculate summary statistics
        risks = report_data.get('risks', [])
        high_risk_count = len([r for r in risks if r.get('inherent_risk_score', 0) >= 16])
        medium_risk_count = len([r for r in risks if 9 <= r.get('inherent_risk_score', 0) < 16])
        low_risk_count = len([r for r in risks if r.get('inherent_risk_score', 0) < 9])
        
        treatment_distribution = {}
        for risk in risks:
            strategy = risk.get('treatment_strategy', 'Not specified')
            treatment_distribution[strategy] = treatment_distribution.get(strategy, 0) + 1
        
        template = Template(html_template)
        html_content = template.render(
            title=report_data.get('title', 'Risk Assessment Report'),
            organization=report_data.get('organization', 'Organization'),
            created_by=report_data.get('created_by', {'name': 'Unknown'}),
            created_at=report_data.get('created_at', datetime.utcnow()),
            status=report_data.get('status', 'completed'),
            total_risks=report_data.get('total_risks', len(risks)),
            risks=risks,
            ai_summary=report_data.get('ai_summary'),
            current_time=datetime.utcnow(),
            high_risk_count=high_risk_count,
            medium_risk_count=medium_risk_count,
            low_risk_count=low_risk_count,
            treatment_distribution=treatment_distribution
        )
        
        return html_content
        
    except Exception as e:
        logger.error(f"Error generating HTML report from data: {e}")
        raise

async def generate_pdf_report_from_data(report_data: Dict[str, Any]) -> bytes:
    """Generate PDF report from risk data dictionary"""
    try:
        # First generate HTML
        html_content = await generate_html_report_from_data(report_data)
        
        # Convert HTML to PDF using weasyprint
        try:
            from weasyprint import HTML
            pdf_bytes = HTML(string=html_content).write_pdf()
            return pdf_bytes
        except ImportError:
            # Fallback: use reportlab if weasyprint is not available
            return await generate_pdf_with_reportlab_from_data(report_data)
            
    except Exception as e:
        logger.error(f"Error generating PDF report from data: {e}")
        raise

async def generate_pdf_with_reportlab_from_data(report_data: Dict[str, Any]) -> bytes:
    """Generate PDF using ReportLab from risk data dictionary"""
    try:
        from reportlab.lib.pagesizes import letter, A4
        from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib import colors
        from reportlab.lib.units import inch
        from io import BytesIO
        
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4)
        styles = getSampleStyleSheet()
        story = []
        
        # Title
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=18,
            alignment=1,  # Center alignment
            spaceAfter=30,
        )
        
        story.append(Paragraph("ISO 27001 Risk Assessment Report", title_style))
        story.append(Paragraph(report_data.get('title', 'Risk Assessment Report'), styles['Heading2']))
        story.append(Paragraph(report_data.get('organization', 'Organization'), styles['Heading3']))
        story.append(Spacer(1, 20))
        
        # Metadata
        created_by = report_data.get('created_by', {'name': 'Unknown'})
        created_at = report_data.get('created_at', datetime.utcnow())
        
        metadata_data = [
            ['Created by:', created_by.get('name', 'Unknown')],
            ['Created date:', created_at.strftime('%Y-%m-%d %H:%M')],
            ['Status:', report_data.get('status', 'completed')],
            ['Total risks:', str(report_data.get('total_risks', 0))],
            ['Report generated:', datetime.utcnow().strftime('%Y-%m-%d %H:%M')]
        ]
        
        metadata_table = Table(metadata_data, colWidths=[2*inch, 3*inch])
        metadata_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), colors.lightgrey),
            ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        
        story.append(metadata_table)
        story.append(Spacer(1, 30))
        
        # Risk table
        story.append(Paragraph("Risk Register", styles['Heading2']))
        
        risks = report_data.get('risks', [])
        risk_data = [['Risk ID', 'Description', 'Likelihood', 'Impact', 'Score', 'Treatment']]
        for risk in risks:
            likelihood = risk.get('likelihood', {})
            impact = risk.get('impact', {})
            risk_data.append([
                risk.get('risk_id', 'N/A'),
                risk.get('risk_description', '')[:100] + '...' if len(risk.get('risk_description', '')) > 100 else risk.get('risk_description', ''),
                f"{likelihood.get('value', 'N/A')} ({likelihood.get('weight', 'N/A')})",
                f"{impact.get('value', 'N/A')} ({impact.get('weight', 'N/A')})",
                str(risk.get('inherent_risk_score', 'N/A')),
                risk.get('treatment_strategy', 'N/A')
            ])
        
        risk_table = Table(risk_data, colWidths=[0.8*inch, 3*inch, 1*inch, 1*inch, 0.7*inch, 1.2*inch])
        risk_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.green),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('FONTSIZE', (0, 1), (-1, -1), 8),
            ('ALIGN', (1, 1), (1, -1), 'LEFT'),  # Left align description column
        ]))
        
        story.append(risk_table)
        
        # Build PDF
        doc.build(story)
        pdf_bytes = buffer.getvalue()
        buffer.close()
        
        return pdf_bytes
        
    except Exception as e:
        logger.error(f"Error generating PDF with ReportLab from data: {e}")
        raise

async def generate_pdf_report(risk_register: RiskRegister) -> bytes:
    """Generate PDF report"""
    try:
        # First generate HTML
        html_content = await generate_html_report(risk_register)
        
        # Convert HTML to PDF using weasyprint
        try:
            from weasyprint import HTML
            pdf_bytes = HTML(string=html_content).write_pdf()
            return pdf_bytes
        except ImportError:
            # Fallback: use reportlab if weasyprint is not available
            return await generate_pdf_with_reportlab(risk_register)
            
    except Exception as e:
        logger.error(f"Error generating PDF report: {e}")
        raise

async def generate_pdf_with_reportlab(risk_register: RiskRegister) -> bytes:
    """Generate PDF using ReportLab as fallback"""
    try:
        from reportlab.lib.pagesizes import letter, A4
        from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib import colors
        from reportlab.lib.units import inch
        from io import BytesIO
        
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4)
        styles = getSampleStyleSheet()
        story = []
        
        # Title
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=18,
            alignment=1,  # Center alignment
            spaceAfter=30,
        )
        
        story.append(Paragraph("ISO 27001 Risk Assessment Report", title_style))
        story.append(Paragraph(risk_register.title, styles['Heading2']))
        story.append(Paragraph(risk_register.organization, styles['Heading3']))
        story.append(Spacer(1, 20))
        
        # Metadata
        metadata_data = [
            ['Created by:', risk_register.created_by.name],
            ['Created date:', risk_register.created_at.strftime('%Y-%m-%d %H:%M')],
            ['Last updated:', risk_register.updated_at.strftime('%Y-%m-%d %H:%M')],
            ['Status:', risk_register.status],
            ['Total risks:', str(risk_register.total_risks)],
            ['Report generated:', datetime.utcnow().strftime('%Y-%m-%d %H:%M')]
        ]
        
        metadata_table = Table(metadata_data, colWidths=[2*inch, 3*inch])
        metadata_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), colors.lightgrey),
            ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        
        story.append(metadata_table)
        story.append(Spacer(1, 30))
        
        # Risk table
        story.append(Paragraph("Risk Register", styles['Heading2']))
        
        risk_data = [['Risk ID', 'Description', 'Likelihood', 'Impact', 'Score', 'Treatment']]
        for risk in risk_register.risks:
            risk_data.append([
                risk.risk_id,
                risk.risk_description[:100] + '...' if len(risk.risk_description) > 100 else risk.risk_description,
                f"{risk.likelihood.value} ({risk.likelihood.weight})",
                f"{risk.impact.value} ({risk.impact.weight})",
                str(risk.inherent_risk_score),
                risk.treatment_strategy
            ])
        
        risk_table = Table(risk_data, colWidths=[0.8*inch, 3*inch, 1*inch, 1*inch, 0.7*inch, 1.2*inch])
        risk_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.green),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('FONTSIZE', (0, 1), (-1, -1), 8),
            ('ALIGN', (1, 1), (1, -1), 'LEFT'),  # Left align description column
        ]))
        
        story.append(risk_table)
        
        # Build PDF
        doc.build(story)
        pdf_bytes = buffer.getvalue()
        buffer.close()
        
        return pdf_bytes
        
    except Exception as e:
        logger.error(f"Error generating PDF with ReportLab: {e}")
        raise
