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

    # Reduce margins to maximize usable width
    doc = SimpleDocTemplate(
        output_path,
        pagesize=LETTER,
        leftMargin=36,  # 0.5 inch
        rightMargin=36,  # 0.5 inch
        topMargin=54,  # 0.75 inch
        bottomMargin=54  # 0.75 inch
    )

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
        fontSize=9,
        leading=11,
        wordWrap="CJK"
    )

    styleN = styles["BodyText"]
    styleN.wordWrap = "CJK"  

    table_data = [
        [Paragraph(cell_value, styleN) for cell_value in row]
        for row in table_data
    ]

    # Helper to split long text into chunks (by words)
    def split_text(text, max_words=60):
        words = text.split()
        if len(words) <= max_words:
            return [text]
        chunks = []
        for i in range(0, len(words), max_words):
            chunk = " ".join(words[i:i+max_words])
            # Add '...continued' to all but the last chunk
            if i + max_words < len(words):
                chunk += " ...continued"
            chunks.append(chunk)
        return chunks

    for item in report_data["detailed_report"]:
        # Split each long field into chunks
        sentence_chunks = split_text(item.get("Policy Sentence", "N/A"))
        control_chunks = split_text(item.get("Closest Control", "N/A"))
        improvement_chunks = split_text(item.get("Suggested Improvement", "N/A"))
        max_chunks = max(len(sentence_chunks), len(control_chunks), len(improvement_chunks))

        # Pad all lists to same length
        def pad(lst):
            return lst + [""] * (max_chunks - len(lst))
        sentence_chunks = pad(sentence_chunks)
        control_chunks = pad(control_chunks)
        improvement_chunks = pad(improvement_chunks)

        # Only Status and Framework are repeated (not split)
        status = item.get("Status", "N/A")
        framework = item.get("Framework", "N/A")

        for i in range(max_chunks):
            row = [
                Paragraph(sentence_chunks[i], custom_style),
                Paragraph(status if i == 0 else "", custom_style),
                Paragraph(framework if i == 0 else "", custom_style),
                Paragraph(control_chunks[i], custom_style),
                Paragraph(improvement_chunks[i], custom_style),
            ]
            table_data.append(row)

    # Use relative column widths (proportional to available width)
    available_width = doc.width
    # Make 'Sentence' and 'Closest Control' wider for readability
    col_widths = [0.22, 0.10, 0.12, 0.28, 0.28]  # sum to 1.0
    col_widths = [w * available_width for w in col_widths]

    table = Table(table_data, colWidths=col_widths, repeatRows=1)
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#003366")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#ffffff")),  # header row white font
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
        ("WORDWRAP", (0, 0), (-1, -1), True),
    ]))

    elements.append(table)

    # Build with onFirstPage/onLaterPages if you want custom footers/headers
    doc.build(elements)

    return os.path.abspath(output_path)
