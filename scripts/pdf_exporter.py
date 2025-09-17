from reportlab.lib.pagesizes import LETTER
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Table, TableStyle, Spacer, PageBreak, Image
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib import colors
import os
from datetime import datetime


def export_pdf(report_data, client_name="Client"):
    if not os.path.exists("reports"):
        os.makedirs("reports")

    safe_client_name = client_name.replace(" ", "_")
    output_path = f"reports/{safe_client_name}_Compliance_Report.pdf"

    doc = SimpleDocTemplate(output_path, pagesize=LETTER,
                            leftMargin=50, rightMargin=50, topMargin=50, bottomMargin=50)

    styles = getSampleStyleSheet()
    elements = []

    # === COVER PAGE ===
    title_style = styles["Title"]
    title_style.textColor = colors.HexColor("#003366")
    elements.append(Paragraph("Compliance Assessment Report", title_style))
    elements.append(Spacer(1, 12))

    subtitle_style = styles["Normal"]
    elements.append(Paragraph(f"Client: {client_name}", subtitle_style))
    elements.append(Paragraph(f"Generated On: {report_data['executive_summary']['report_generated_at']}", subtitle_style))
    elements.append(Spacer(1, 20))
    elements.append(PageBreak())

    # === EXECUTIVE SUMMARY ===
    heading_style = styles["Heading2"]
    heading_style.textColor = colors.HexColor("#003366")
    elements.append(Paragraph("Executive Summary", heading_style))
    elements.append(Spacer(1, 10))

    for key, value in report_data["executive_summary"].items():
        if key == "report_generated_at":
            continue
        elements.append(Paragraph(f"<b>{key}</b>: {value}", styles["Normal"]))
        elements.append(Spacer(1, 6))

    elements.append(PageBreak())

    # === CONTROL COVERAGE REPORT ===
    elements.append(Paragraph("Control Coverage Report", heading_style))
    elements.append(Spacer(1, 12))

    # Table headers and body
    table_data = [["Sentence", "Status", "Framework", "Closest Control", "Suggested Improvement"]]

    custom_style = ParagraphStyle(
        name="Wrapped",
        parent=styles["Normal"],
        fontSize=8,
        leading=10,
        wordWrap="CJK"
    )

    for item in report_data["detailed_report"]:
        row = [
            Paragraph(item.get("Policy Sentence", "N/A"), custom_style),
            Paragraph(item.get("Status", "N/A"), custom_style),
            Paragraph(item.get("Framework", "N/A"), custom_style),
            Paragraph(item.get("Closest Control", "N/A"), custom_style),
            Paragraph(item.get("Suggested Improvement", "N/A"), custom_style),
        ]
        table_data.append(row)

    table = Table(table_data, colWidths=[2.8 * inch, 0.8 * inch, 1.0 * inch, 1.5 * inch, 2.0 * inch], repeatRows=1)
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#003366")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
        ("ALIGN", (0, 0), (-1, -1), "LEFT"),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, 0), 9),
        ("FONTSIZE", (0, 1), (-1, -1), 8),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.whitesmoke, colors.lightgrey]),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))

    elements.append(table)

    doc.build(elements)

    return os.path.abspath(output_path)
