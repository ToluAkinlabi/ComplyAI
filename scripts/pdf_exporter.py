from datetime import datetime
from typing import Any, Dict, List

from reportlab.lib.pagesizes import LETTER
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_JUSTIFY
import os
import logging

logger = logging.getLogger(__name__)

def export_pdf(report_data: Dict[str, Any], client_name: str) -> str:
    """Export compliance report to PDF with improved table handling"""
    try:
        # Validate input data
        if not isinstance(report_data, dict):
            raise ValueError("Invalid report data format")
        
        detailed_report = report_data.get("detailed_report", [])
        if not isinstance(detailed_report, list):
            raise ValueError("Invalid detailed report format")

        # Create safe filename
        safe_client_name = "".join(c for c in client_name if c.isalnum() or c in (' ', '-', '_')).strip()
        if not safe_client_name:
            safe_client_name = "Client"
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{safe_client_name}_Compliance_Report_{timestamp}.pdf"
        output_path = os.path.join("reports", filename)
        
        # Ensure reports directory exists
        os.makedirs("reports", exist_ok=True)
        
        # Create PDF document
        doc = SimpleDocTemplate(
            output_path,
            pagesize=LETTER,
            rightMargin=0.5*inch,
            leftMargin=0.5*inch,
            topMargin=0.75*inch,
            bottomMargin=0.75*inch
        )
        
        # Define styles
        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=18,
            spaceAfter=20,
            alignment=TA_CENTER,
            textColor=colors.darkblue
        )
        
        heading_style = ParagraphStyle(
            'CustomHeading',
            parent=styles['Heading2'],
            fontSize=14,
            spaceAfter=12,
            spaceBefore=12,
            textColor=colors.darkblue
        )
        
        body_style = ParagraphStyle(
            'CustomBody',
            parent=styles['Normal'],
            fontSize=10,
            spaceAfter=6,
            alignment=TA_JUSTIFY
        )
        
        # Enhanced table text style for better wrapping
        table_text_style = ParagraphStyle(
            'TableText',
            parent=styles['Normal'],
            fontSize=8,
            leading=10,
            wordWrap='CJK',
            allowWidows=1,
            allowOrphans=1,
            spaceAfter=2,
            spaceBefore=2
        )
        
        # Build document content
        story = []
        
        # Title page
        story.append(Paragraph("ComplyAI Compliance Analysis Report", title_style))
        story.append(Spacer(1, 0.25*inch))
        
        # Client info
        metadata = report_data.get("metadata", {})
        client_info = f"""
        <b>Client:</b> {client_name}<br/>
        <b>Document:</b> {metadata.get('document_name', 'Unknown')}<br/>
        <b>Generated:</b> {metadata.get('report_generated_at', 'Unknown')}<br/>
        <b>Processing Time:</b> {metadata.get('processing_time_seconds', 0)} seconds<br/>
        <b>Model Used:</b> {metadata.get('model_used', 'Unknown')}
        """
        story.append(Paragraph(client_info, body_style))
        story.append(Spacer(1, 0.3*inch))
        
        # Executive Summary
        story.append(Paragraph("Executive Summary", heading_style))
        exec_summary = report_data.get("executive_summary", "No summary available.")
        # Clean up the executive summary formatting
        exec_summary_clean = exec_summary.replace('\n', '<br/>')
        story.append(Paragraph(exec_summary_clean, body_style))
        story.append(PageBreak())
        
        # Detailed Findings
        story.append(Paragraph("Detailed Policy Analysis", heading_style))
        
        if detailed_report:
            # Create table with truncated content to avoid overflow
            table_data = [["Status", "Priority", "Framework", "Control ID", "Policy Statement", "Suggested Improvement"]]
            
            for i, rec in enumerate(detailed_report):
                if not isinstance(rec, dict):
                    continue
                
                # Truncate long text fields to prevent table overflow, but allow control_id to wrap
                status = str(rec.get("status", "Unknown"))[:20]
                priority = str(rec.get("priority", "Unknown"))[:15]
                framework = str(rec.get("framework", "Unknown"))[:25]
                
                # Don't truncate control_id, use Paragraph for wrapping instead
                control_id_text = str(rec.get("control_id", "Unknown"))
                control_id_para = Paragraph(control_id_text, table_text_style)
                
                # Truncate and clean policy statement
                policy = str(rec.get("sentence", ""))[:200]
                if len(str(rec.get("sentence", ""))) > 200:
                    policy += "..."
                policy = policy.replace('\n', ' ').replace('\r', ' ')
                
                # Truncate and clean improvement suggestion
                improvement = str(rec.get("suggested_improvement", ""))[:250]
                if len(str(rec.get("suggested_improvement", ""))) > 250:
                    improvement += "..."
                improvement = improvement.replace('\n', ' ').replace('\r', ' ')
                
                # Create paragraphs for better text wrapping
                policy_para = Paragraph(policy, table_text_style)
                improvement_para = Paragraph(improvement, table_text_style)
                
                table_data.append([
                    status,
                    priority,
                    framework,
                    control_id_para,
                    policy_para,
                    improvement_para
                ])
                
                # Limit to 50 rows to prevent PDF size issues
                if i >= 49:
                    remaining = len(detailed_report) - i - 1
                    if remaining > 0:
                        table_data.append([
                            "...", "...", "...", 
                            Paragraph("...", table_text_style),
                            Paragraph(f"... and {remaining} more items", table_text_style),
                            Paragraph("See JSON report for complete details", table_text_style)
                        ])
                    break
            
            # Create table with appropriate column widths - more space for Control ID
            col_widths = [0.7*inch, 0.7*inch, 1.1*inch, 1.3*inch, 2.1*inch, 2.1*inch]
            
            table = Table(table_data, colWidths=col_widths, repeatRows=1)
            
            # Apply table style
            table.setStyle(TableStyle([
                # Header row styling
                ('BACKGROUND', (0, 0), (-1, 0), colors.darkblue),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 9),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                
                # Data rows styling
                ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 1), (-1, -1), 8),
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ('LEFTPADDING', (0, 0), (-1, -1), 4),
                ('RIGHTPADDING', (0, 0), (-1, -1), 4),
                ('TOPPADDING', (0, 0), (-1, -1), 4),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
                
                # Alternating row colors
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.lightgrey]),
            ]))
            
            story.append(table)
        else:
            story.append(Paragraph("No detailed findings available.", body_style))
        
        # Footer
        story.append(Spacer(1, 0.5*inch))
        footer_text = f"Report generated by ComplyAI v2.0.0 on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        story.append(Paragraph(footer_text, ParagraphStyle('Footer', fontSize=8, textColor=colors.grey)))
        
        # Build PDF
        doc.build(story)
        
        logger.info(f"✅ PDF report exported successfully: {output_path}")
        return output_path
        
    except Exception as e:
        logger.error(f"❌ Failed to export PDF: {e}")
        raise Exception(f"PDF export failed: {str(e)}")

def _safe_paragraph(text: str, style, max_length: int = 500) -> Paragraph:
    """Create a safe paragraph with length limits"""
    if not text:
        text = "N/A"
    
    # Truncate and clean text
    clean_text = str(text)[:max_length].replace('\n', ' ').replace('\r', ' ')
    if len(str(text)) > max_length:
        clean_text += "..."
    
    return Paragraph(clean_text, style)