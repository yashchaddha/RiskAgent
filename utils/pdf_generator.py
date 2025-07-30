import io
import os
import tempfile
from datetime import datetime
from typing import Dict, Any, Optional
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib.colors import HexColor, black, blue, red, green
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
from reportlab.platypus.tableofcontents import TableOfContents
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_JUSTIFY
import re
from config import get_logger

logger = get_logger(__name__)

class RiskReportPDFGenerator:
    """Generate professional PDF reports from risk management text"""
    
    def __init__(self):
        self.styles = getSampleStyleSheet()
        self._setup_custom_styles()
    
    def _setup_custom_styles(self):
        """Setup custom paragraph styles for the report"""
        
        # Title page styles
        self.styles.add(ParagraphStyle(
            name='ReportTitle',
            parent=self.styles['Title'],
            fontSize=24,
            spaceAfter=30,
            alignment=TA_CENTER,
            textColor=HexColor('#2c3e50')
        ))
        
        self.styles.add(ParagraphStyle(
            name='CompanyName',
            parent=self.styles['Heading1'],
            fontSize=18,
            spaceAfter=20,
            alignment=TA_CENTER,
            textColor=HexColor('#34495e')
        ))
        
        # Section headers
        self.styles.add(ParagraphStyle(
            name='SectionHeader',
            parent=self.styles['Heading1'],
            fontSize=16,
            spaceBefore=20,
            spaceAfter=12,
            textColor=HexColor('#2c3e50'),
            borderWidth=1,
            borderColor=HexColor('#bdc3c7'),
            borderPadding=8
        ))
        
        self.styles.add(ParagraphStyle(
            name='SubSectionHeader',
            parent=self.styles['Heading2'],
            fontSize=14,
            spaceBefore=15,
            spaceAfter=8,
            textColor=HexColor('#34495e')
        ))
        
        # Body text styles
        self.styles.add(ParagraphStyle(
            name='BodyJustified',
            parent=self.styles['Normal'],
            fontSize=11,
            spaceAfter=12,
            alignment=TA_JUSTIFY,
            leftIndent=0,
            rightIndent=0
        ))
        
        # Risk item styles
        self.styles.add(ParagraphStyle(
            name='RiskDescription',
            parent=self.styles['Normal'],
            fontSize=11,
            spaceBefore=8,
            spaceAfter=4,
            leftIndent=20
        ))
        
        # Footer style
        self.styles.add(ParagraphStyle(
            name='Footer',
            parent=self.styles['Normal'],
            fontSize=9,
            alignment=TA_CENTER,
            textColor=HexColor('#7f8c8d')
        ))

    def generate_pdf(self, report_content: str, user_data: dict, output_path: Optional[str] = None) -> str:
        logger.info(f"Generating PDF report for {user_data.get('organization', 'Unknown')}")
        
        try:
            # Create output file
            if output_path is None:
                # Create temporary file
                fd, output_path = tempfile.mkstemp(suffix='.pdf', prefix='risk_report_')
                os.close(fd)
            
            # Create PDF document
            doc = SimpleDocTemplate(
                output_path,
                pagesize=A4,
                rightMargin=72,
                leftMargin=72,
                topMargin=72,
                bottomMargin=72
            )
            
            # Build the story (content)
            story = []
            
            # Title page
            story.extend(self._create_title_page(user_data))
            story.append(PageBreak())
            
            # Parse and add report content
            story.extend(self._parse_report_content(report_content))
            
            # Build PDF
            doc.build(story)
            
            logger.info(f"PDF report generated successfully: {output_path}")
            return output_path
            
        except Exception as e:
            logger.error(f"PDF generation error: {str(e)}", exc_info=True)
            raise Exception(f"Failed to generate PDF: {str(e)}")
    
    def _create_title_page(self, user_data: dict) -> list:
        """Create the title page elements"""
        
        story = []
        
        # Add some space from top
        story.append(Spacer(1, 100))
        
        # Report title
        story.append(Paragraph("Risk Management Report", self.styles['ReportTitle']))
        story.append(Spacer(1, 40))
        
        # Organization name
        org_name = user_data.get('organization', 'Organization')
        story.append(Paragraph(f"{org_name}", self.styles['CompanyName']))
        story.append(Spacer(1, 30))
        
        # Report details table
        report_details = [
            ['Industry:', user_data.get('industry', 'Not specified')],
            ['Assessment Date:', user_data.get('assessment_date', datetime.now().strftime('%B %Y'))],
            ['Matrix Size:', user_data.get('matrix_size', '3x3')],
            ['Generated:', datetime.now().strftime('%B %d, %Y at %I:%M %p')]
        ]
        
        details_table = Table(report_details, colWidths=[2*inch, 3*inch])
        details_table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTNAME', (1, 0), (1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 12),
            ('GRID', (0, 0), (-1, -1), 1, HexColor('#bdc3c7')),
            ('BACKGROUND', (0, 0), (0, -1), HexColor('#ecf0f1')),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('LEFTPADDING', (0, 0), (-1, -1), 10),
            ('RIGHTPADDING', (0, 0), (-1, -1), 10),
            ('TOPPADDING', (0, 0), (-1, -1), 8),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8)
        ]))
        
        story.append(details_table)
        story.append(Spacer(1, 60))
        
        # Disclaimer
        disclaimer = """This risk management report has been generated using AI-assisted analysis. 
        It should be reviewed by qualified risk management professionals and adapted to your 
        organization's specific requirements and regulatory environment."""
        
        story.append(Paragraph(disclaimer, self.styles['BodyJustified']))
        
        return story
    
    def _parse_report_content(self, content: str) -> list:
        """Parse the report content and convert to PDF elements"""
        
        story = []
        lines = content.split('\n')
        current_section = []
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
                
            # Check for different heading levels
            if line.startswith('# '):
                # Main section header
                if current_section:
                    story.extend(self._process_section(current_section))
                    current_section = []
                story.append(Paragraph(line[2:], self.styles['SectionHeader']))
                story.append(Spacer(1, 12))
                
            elif line.startswith('## '):
                # Sub-section header
                if current_section:
                    story.extend(self._process_section(current_section))
                    current_section = []
                story.append(Paragraph(line[3:], self.styles['SubSectionHeader']))
                story.append(Spacer(1, 8))
                
            elif line.startswith('**') and line.endswith('**'):
                # Bold headers
                if current_section:
                    story.extend(self._process_section(current_section))
                    current_section = []
                header_text = line[2:-2]
                story.append(Paragraph(f"<b>{header_text}</b>", self.styles['SubSectionHeader']))
                story.append(Spacer(1, 8))
                
            elif line.startswith('- ') or line.startswith('• '):
                # Bullet points
                bullet_text = line[2:] if line.startswith('- ') else line[2:]
                story.append(Paragraph(f"• {bullet_text}", self.styles['RiskDescription']))
                
            elif line.startswith('✅'):
                # Check mark items
                check_text = line[2:].strip()
                story.append(Paragraph(f"✓ {check_text}", self.styles['RiskDescription']))
                
            elif '|' in line and line.count('|') >= 2:
                # Table row - collect for table processing
                current_section.append(line)
                
            else:
                # Regular paragraph
                if current_section:
                    story.extend(self._process_section(current_section))
                    current_section = []
                if line:
                    # Clean up markdown formatting
                    cleaned_line = self._clean_markdown(line)
                    story.append(Paragraph(cleaned_line, self.styles['BodyJustified']))
                    story.append(Spacer(1, 6))
        
        # Process any remaining section
        if current_section:
            story.extend(self._process_section(current_section))
        
        return story
    
    def _process_section(self, section_lines: list) -> list:
        """Process a section that might contain tables"""
        
        story = []
        
        # Check if this looks like a table
        if any('|' in line and line.count('|') >= 2 for line in section_lines):
            # Process as table
            table_data = []
            for line in section_lines:
                if '|' in line:
                    # Split by | and clean up
                    cells = [cell.strip() for cell in line.split('|') if cell.strip()]
                    if cells and not all(cell == '-' or cell == '' for cell in cells):
                        table_data.append(cells)
            
            if table_data:
                # Create table
                table = Table(table_data)
                table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), HexColor('#34495e')),
                    ('TEXTCOLOR', (0, 0), (-1, 0), HexColor('#ffffff')),
                    ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                    ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
                    ('FONTSIZE', (0, 0), (-1, -1), 10),
                    ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                    ('GRID', (0, 0), (-1, -1), 1, HexColor('#bdc3c7')),
                    ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                    ('LEFTPADDING', (0, 0), (-1, -1), 8),
                    ('RIGHTPADDING', (0, 0), (-1, -1), 8)
                ]))
                story.append(table)
                story.append(Spacer(1, 12))
        
        return story
    
    def _clean_markdown(self, text: str) -> str:
        """Clean markdown formatting for PDF"""
        
        # Bold text
        text = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', text)
        
        # Italic text
        text = re.sub(r'\*(.*?)\*', r'<i>\1</i>', text)
        
        # Remove markdown links but keep text
        text = re.sub(r'\[([^\]]+)\]\([^\)]+\)', r'\1', text)
        
        return text


def generate_risk_report_pdf(report_content: str, user_data: dict, output_dir: str = None) -> str:
    """
    Convenience function to generate a risk report PDF
    
    Args:
        report_content: The report text content
        user_data: User and organization data
        output_dir: Directory to save the PDF (optional)
        
    Returns:
        str: Path to the generated PDF file
    """
    
    generator = RiskReportPDFGenerator()
    
    # Determine output path
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        org_name = user_data.get('organization', 'report').replace(' ', '_').lower()
        filename = f"risk_report_{org_name}_{timestamp}.pdf"
        output_path = os.path.join(output_dir, filename)
    else:
        output_path = None
    
    return generator.generate_pdf(report_content, user_data, output_path)