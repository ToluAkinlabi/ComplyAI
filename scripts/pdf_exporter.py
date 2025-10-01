import os
import re
from datetime import datetime
from typing import Any, Dict, List

from reportlab.lib.pagesizes import LETTER
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Table, TableStyle, Spacer, PageBreak
from reportlab.pdfgen import canvas

def _safe(text: Any) -> str:
    if text is None:
        return ""
    s = str(text)
    return s.replace("<", "&lt;").replace(">", "&gt;")

def _page_number(c: canvas.Canvas, doc):
    c.setFont("Helvetica", 8)
    c.drawRightString(7.95 * inch, 0.4 * inch, f"Page {doc.page}")

def export_pdf(report_data: Dict[str, Any], client_name: str = "Client") -> str:
    os.makedirs("reports", exist_ok=True)
    safe_client_name = re.sub(r"[^A-Za-z0-9_\-]+", "_", client_name.strip()) or "Client"
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_path = f"reports/{safe_client_name}_Compliance_Report_{timestamp}.pdf"

    doc = SimpleDocTemplate(
        output_path,
        pagesize=LETTER,
        leftMargin=0.5 * inch,
        rightMargin=0.5 * inch,
        topMargin=0.6 * inch,
        bottomMargin=0.6 * inch,
        title=f"{client_name} Compliance Report",
        author="ComplyAI",
    )

    styles = getSampleStyleSheet()
    h1 = ParagraphStyle("H1", parent=styles["Heading1"], fontName="Helvetica-Bold", fontSize=18, spaceAfter=12)
    h2 = ParagraphStyle("H2", parent=styles["Heading2"], fontName="Helvetica-Bold", fontSize=14, spaceBefore=6, spaceAfter=6)
    body = ParagraphStyle("Body", parent=styles["BodyText"], fontName="Helvetica", fontSize=10, leading=13, spaceAfter=6)
    small = ParagraphStyle("Small", parent=styles["BodyText"], fontName="Helvetica", fontSize=9, leading=12)

    elements: List[Any] = []

    # Title + timestamp (from metadata when available)
    elements.append(Paragraph(f"{_safe(client_name)} - Compliance Analysis Report", h1))
    generated_at = _safe(report_data.get("metadata", {}).get("report_generated_at", datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
    elements.append(Paragraph(generated_at, small))
    elements.append(Spacer(1, 8))

    # Executive Summary (string or dict)
    elements.append(Paragraph("Executive Summary", h2))
    summary = report_data.get("executive_summary", "")
    if isinstance(summary, dict):
        for k, v in summary.items():
            if k == "report_generated_at":
                continue
            elements.append(Paragraph(f"<b>{_safe(k)}</b>: {_safe(v)}", body))
    else:
        for line in str(summary).splitlines():
            if line.strip():
                elements.append(Paragraph(_safe(line), body))
    elements.append(Spacer(1, 10))

    # Metadata
    meta = report_data.get("metadata", {}) or {}
    meta_lines = [
        f"Client: {_safe(meta.get('client_name', client_name))}",
        f"Document: {_safe(meta.get('document_name', 'Unknown'))}",
        f"Total Sentences: {_safe(meta.get('total_sentences', 0))}",
        f"Processed Sentences: {_safe(meta.get('processed_sentences', 0))}",
        f"Total Recommendations: {_safe(meta.get('total_recommendations', 0))}",
    ]
    for l in meta_lines:
        elements.append(Paragraph(l, small))
    elements.append(Spacer(1, 10))

    # Detailed Findings
    elements.append(Paragraph("Detailed Findings", h2))
    findings = report_data.get("detailed_report", []) or []
    if not isinstance(findings, list) or not findings:
        elements.append(Paragraph("No findings available.", body))
    else:
        # Helper to read either style of keys
        def get_field(item: Dict[str, Any], *candidates: str, default: str = "") -> str:
            for k in candidates:
                if k in item and item[k]:
                    return str(item[k])
            return default

        table_data = [[
            Paragraph("Status", small),
            Paragraph("Priority", small),
            Paragraph("Similarity", small),
            Paragraph("Framework / Control", small),
            Paragraph("Policy Sentence", small),
            Paragraph("Suggested Improvement", small),
        ]]

        for rec in findings:
            if not isinstance(rec, dict):
                continue

            status     = get_field(rec, "Status", "status")
            priority   = get_field(rec, "Priority", "priority")
            sim        = get_field(rec, "similarity_score", "similarity", default="0.00")
            framework  = get_field(rec, "Framework", "framework", default="")
            control_id = get_field(rec, "control_id", "Control Id", "Control", default="")
            fw_label   = f"{framework} / {control_id}" if framework or control_id else ""

            sentence   = Paragraph(_safe(get_field(rec, "Policy Sentence", "sentence")), body)
            suggestion = Paragraph(_safe(get_field(rec, "Suggested Improvement", "suggested_improvement")), body)

            table_data.append([
                Paragraph(_safe(status), body),
                Paragraph(_safe(priority), body),
                Paragraph(_safe(sim), body),
                Paragraph(_safe(fw_label), body),
                sentence,
                suggestion,
            ])

        col_widths = [0.9 * inch, 0.9 * inch, 0.8 * inch, 1.4 * inch, 2.3 * inch, 1.2 * inch]
        table = Table(table_data, colWidths=col_widths, repeatRows=1)
        table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#F2F2F2")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#333333")),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 9),
            ("ALIGN", (2, 1), (2, -1), "RIGHT"),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("LINEBELOW", (0, 0), (-1, 0), 0.5, colors.HexColor("#CCCCCC")),
            ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#DDDDDD")),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#FBFBFB")]),
        ]))
        elements.append(table)

    # Optional page break to end cleanly
    elements.append(PageBreak())

    doc.build(elements, onFirstPage=_page_number, onLaterPages=_page_number)
    return output_path
