from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table,
    TableStyle, HRFlowable, Image as RLImage
)
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT
from reportlab.graphics.shapes import Drawing, Rect
from reportlab.graphics import renderPDF
import io
import base64
import datetime
from PIL import Image as PILImage


C_DARK    = colors.HexColor("#0A0E1A")
C_BLUE    = colors.HexColor("#0891B2")
C_CYAN    = colors.HexColor("#06B6D4")
C_LIGHT   = colors.HexColor("#E0F7FA")
C_GREEN   = colors.HexColor("#14532D")
C_GREEN_L = colors.HexColor("#D1FAE5")
C_RED     = colors.HexColor("#7F1D1D")
C_RED_L   = colors.HexColor("#FEE2E2")
C_AMBER   = colors.HexColor("#78350F")
C_AMBER_L = colors.HexColor("#FEF3C7")
C_GRAY    = colors.HexColor("#475569")
C_LGRAY   = colors.HexColor("#F8FAFC")
C_BORDER  = colors.HexColor("#E2E8F0")
C_WHITE   = colors.white
C_NAVY    = colors.HexColor("#0C1A2E")


def verdict_colors(verdict: str):
    if verdict == "real":       return colors.HexColor("#166534"), colors.HexColor("#D1FAE5")
    if verdict == "fake":       return colors.HexColor("#991B1B"), colors.HexColor("#FEE2E2")
    if verdict == "suspicious": return colors.HexColor("#92400E"), colors.HexColor("#FEF3C7")
    return C_GRAY, C_LGRAY


def verdict_label(verdict: str) -> str:
    return {"real":"AUTHENTIC","fake":"FAKE / MANIPULATED","suspicious":"SUSPICIOUS","error":"ERROR"}.get(verdict, verdict.upper())


def generate_pdf_report(result: dict) -> bytes:
    buf     = io.BytesIO()
    verdict = result.get("verdict", "error")
    vc, vcl = verdict_colors(verdict)

    doc = SimpleDocTemplate(
        buf, pagesize=A4,
        rightMargin=18*mm, leftMargin=18*mm,
        topMargin=18*mm,   bottomMargin=18*mm,
        title=f"TruthLens — {result.get('filename','report')}",
    )

    story = []
    story += build_header(result, vc)
    story.append(Spacer(1, 5*mm))
    story += build_verdict_banner(verdict, result, vc, vcl)
    story.append(Spacer(1, 5*mm))

    if result.get("ai_summary"):
        story += build_ai_summary(result["ai_summary"])
        story.append(Spacer(1, 4*mm))

    story += build_metadata_table(result)
    story.append(Spacer(1, 5*mm))

    if result.get("signals"):
        story += build_signals(result["signals"])
        story.append(Spacer(1, 5*mm))

    # Only build heatmap if it exists and is not empty
    heatmap = result.get("heatmap_b64")
    if heatmap and isinstance(heatmap, str) and len(heatmap) > 100:
        story += build_heatmap(heatmap, result.get("engine", "image"))
        story.append(Spacer(1, 5*mm))

    if result.get("findings"):
        story += build_findings(result["findings"], vc)
        story.append(Spacer(1, 5*mm))

    story += build_footer()
    doc.build(story)
    return buf.getvalue()


def build_header(result, vc):
    items = []
    logo_style = ParagraphStyle("logo", fontSize=20, fontName="Helvetica-Bold", textColor=C_DARK, leading=24)
    sub_style  = ParagraphStyle("sub",  fontSize=9,  fontName="Helvetica",      textColor=C_GRAY, leading=12)
    date_style = ParagraphStyle("date", fontSize=9,  fontName="Helvetica",      textColor=C_GRAY, alignment=TA_RIGHT)

    now   = datetime.datetime.now().strftime("%B %d, %Y at %I:%M %p")
    logo  = Paragraph('<font color="#0891B2">Truth</font>Lens', logo_style)
    sub   = Paragraph("AI-Powered Authenticity Detection — Evidence Report", sub_style)
    date  = Paragraph(f"Generated: {now}", date_style)

    t = Table([[logo, date]], colWidths=[120*mm, 54*mm])
    t.setStyle(TableStyle([("VALIGN",(0,0),(-1,-1),"MIDDLE"),("ALIGN",(1,0),(1,0),"RIGHT")]))
    items.append(t)
    items.append(Spacer(1, 2*mm))
    items.append(sub)
    items.append(Spacer(1, 2*mm))
    items.append(HRFlowable(width="100%", thickness=1, color=C_BORDER))
    return items


def build_verdict_banner(verdict, result, vc, vcl):
    items = []
    icon  = {"real":"✓","fake":"✕","suspicious":"?","error":"!"}.get(verdict,"?")
    label = verdict_label(verdict)
    conf  = result.get("confidence", 0)
    score = result.get("fake_score", 0)

    title_style = ParagraphStyle("vt", fontSize=18, fontName="Helvetica-Bold", textColor=vc, leading=22)
    meta_style  = ParagraphStyle("vm", fontSize=10, fontName="Helvetica",      textColor=vc, alignment=TA_RIGHT, leading=14)

    data = [[
        Paragraph(f"{icon}  {label}", title_style),
        Paragraph(f"<b>{conf}%</b> confidence<br/>Risk score: <b>{score}/100</b><br/>Engine: <b>{result.get('engine','N/A').upper()}</b>", meta_style),
    ]]
    t = Table(data, colWidths=[110*mm, 64*mm])
    t.setStyle(TableStyle([
        ("BACKGROUND",    (0,0),(-1,-1), vcl),
        ("TOPPADDING",    (0,0),(-1,-1), 10),
        ("BOTTOMPADDING", (0,0),(-1,-1), 10),
        ("LEFTPADDING",   (0,0),(-1,-1), 14),
        ("RIGHTPADDING",  (0,0),(-1,-1), 14),
        ("VALIGN",        (0,0),(-1,-1), "MIDDLE"),
        ("BOX",           (0,0),(-1,-1), 1, vc),
    ]))
    items.append(t)
    return items


def build_ai_summary(summary: str):
    items = []
    label_s = ParagraphStyle("lbl", fontSize=9,  fontName="Helvetica-Bold", textColor=C_BLUE, leading=12)
    text_s  = ParagraphStyle("txt", fontSize=10, fontName="Helvetica",      textColor=C_DARK, leading=14)
    items.append(Paragraph("GROQ AI ANALYSIS", label_s))
    items.append(Spacer(1, 2*mm))

    # Sanitize summary — remove any non-latin chars that could crash reportlab
    safe_summary = "".join(c if ord(c) < 65536 else "?" for c in str(summary))

    data = [[Paragraph(safe_summary, text_s)]]
    t    = Table(data, colWidths=[174*mm])
    t.setStyle(TableStyle([
        ("BACKGROUND",    (0,0),(-1,-1), C_LIGHT),
        ("LEFTPADDING",   (0,0),(-1,-1), 12),
        ("RIGHTPADDING",  (0,0),(-1,-1), 12),
        ("TOPPADDING",    (0,0),(-1,-1), 8),
        ("BOTTOMPADDING", (0,0),(-1,-1), 8),
        ("BOX",           (0,0),(-1,-1), 1, C_BLUE),
    ]))
    items.append(t)
    return items


def build_metadata_table(result):
    items = []
    label_s = ParagraphStyle("lbl", fontSize=9, fontName="Helvetica-Bold", textColor=C_GRAY, leading=12)
    val_s   = ParagraphStyle("val", fontSize=9, fontName="Helvetica",      textColor=C_DARK, leading=12)
    items.append(Paragraph("FILE INFORMATION", label_s))
    items.append(Spacer(1, 2*mm))

    rows = [
        ["Filename",      result.get("filename",  "N/A")],
        ["Engine",        result.get("engine",    "N/A").upper()],
        ["Verdict",       verdict_label(result.get("verdict","error"))],
        ["Confidence",    f"{result.get('confidence', 0)}%"],
        ["Risk score",    f"{result.get('fake_score', 0)} / 100"],
        ["Groq AI",       "Active" if result.get("groq_active") else "Inactive"],
        ["Analyzed",      datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")],
    ]
    if result.get("frames_analyzed"):
        rows.append(["Frames", str(result["frames_analyzed"])])
    if result.get("word_count"):
        rows.append(["Word count", str(result["word_count"])])

    table_data = [[Paragraph(f"<b>{r[0]}</b>", val_s), Paragraph(str(r[1]), val_s)] for r in rows]
    t = Table(table_data, colWidths=[45*mm, 129*mm])
    t.setStyle(TableStyle([
        ("BACKGROUND",    (0,0),(0,-1),  C_LGRAY),
        ("FONTNAME",      (0,0),(0,-1),  "Helvetica-Bold"),
        ("FONTSIZE",      (0,0),(-1,-1), 9),
        ("TOPPADDING",    (0,0),(-1,-1), 5),
        ("BOTTOMPADDING", (0,0),(-1,-1), 5),
        ("LEFTPADDING",   (0,0),(-1,-1), 8),
        ("RIGHTPADDING",  (0,0),(-1,-1), 8),
        ("GRID",          (0,0),(-1,-1), 0.5, C_BORDER),
        ("ROWBACKGROUNDS",(0,0),(-1,-1), [C_WHITE, C_LGRAY]),
    ]))
    items.append(t)
    return items


def build_signals(signals: list):
    items = []
    label_s = ParagraphStyle("lbl",  fontSize=9, fontName="Helvetica-Bold", textColor=C_GRAY,  leading=12)
    name_s  = ParagraphStyle("name", fontSize=9, fontName="Helvetica",      textColor=C_DARK,  leading=12)
    val_s   = ParagraphStyle("val",  fontSize=9, fontName="Helvetica-Bold", textColor=C_DARK,  leading=12, alignment=TA_RIGHT)

    items.append(Paragraph("SIGNAL BREAKDOWN", label_s))
    items.append(Spacer(1, 2*mm))

    def bar_color(v):
        if v >= 60: return colors.HexColor("#EF4444")
        if v >= 35: return colors.HexColor("#F59E0B")
        return colors.HexColor("#22C55E")

    rows = []
    for s in signals:
        val   = s.get("value", 0)
        name  = s.get("name",  "Signal")
        col   = bar_color(val)
        bar_w = 80*mm
        filled = (val / 100) * bar_w

        d = Drawing(bar_w, 8)
        d.add(Rect(0, 1, bar_w, 6, fillColor=C_BORDER, strokeColor=None))
        if filled > 0:
            d.add(Rect(0, 1, filled, 6, fillColor=col, strokeColor=None))

        rows.append([Paragraph(name, name_s), d, Paragraph(f"<b>{val}%</b>", val_s)])

    t = Table(rows, colWidths=[60*mm, 88*mm, 26*mm])
    t.setStyle(TableStyle([
        ("VALIGN",        (0,0),(-1,-1), "MIDDLE"),
        ("TOPPADDING",    (0,0),(-1,-1), 5),
        ("BOTTOMPADDING", (0,0),(-1,-1), 5),
        ("LEFTPADDING",   (0,0),(-1,-1), 0),
        ("LINEBELOW",     (0,0),(-1,-2), 0.3, C_BORDER),
    ]))
    items.append(t)
    return items


def build_heatmap(heatmap_b64: str, engine: str):
    items = []
    label_s = ParagraphStyle("lbl", fontSize=9, fontName="Helvetica-Bold", textColor=C_GRAY,  leading=12)
    cap_s   = ParagraphStyle("cap", fontSize=8, fontName="Helvetica",      textColor=C_GRAY,  alignment=TA_CENTER, leading=10)

    label   = "ELA HEATMAP" if engine == "image" else "VIDEO FRAME THUMBNAIL"
    caption = (
        "Red/warm zones indicate regions with high manipulation probability."
        if engine == "image"
        else "First frame extracted from video for visual reference."
    )

    items.append(Paragraph(label, label_s))
    items.append(Spacer(1, 2*mm))

    try:
        # Decode base64 safely
        img_bytes = base64.b64decode(heatmap_b64)
        pil_img   = PILImage.open(io.BytesIO(img_bytes)).convert("RGB")

        # Resize to fit page width
        max_w = 174 * mm
        max_h = 80  * mm
        w, h  = pil_img.size
        ratio = min(max_w / w, max_h / h)
        new_w = int(w * ratio)
        new_h = int(h * ratio)
        pil_img = pil_img.resize((new_w, new_h), PILImage.LANCZOS)

        buf2 = io.BytesIO()
        pil_img.save(buf2, format="JPEG", quality=85)
        buf2.seek(0)

        rl_img = RLImage(buf2, width=new_w, height=new_h)
        items.append(rl_img)
        items.append(Spacer(1, 2*mm))
        items.append(Paragraph(caption, cap_s))

    except Exception as e:
        err_s = ParagraphStyle("err", fontSize=9, fontName="Helvetica", textColor=C_GRAY)
        items.append(Paragraph(f"Heatmap unavailable: {str(e)}", err_s))

    return items


def build_findings(findings: list, vc):
    items = []
    label_s = ParagraphStyle("lbl",  fontSize=9, fontName="Helvetica-Bold", textColor=C_GRAY, leading=12)
    find_s  = ParagraphStyle("find", fontSize=9, fontName="Helvetica",      textColor=C_DARK, leading=14)

    items.append(Paragraph("KEY FINDINGS", label_s))
    items.append(Spacer(1, 2*mm))

    rows = []
    for f in findings:
        if not f:
            continue
        dot_s = ParagraphStyle("dot", fontSize=10, fontName="Helvetica", textColor=vc, leading=14)
        # Sanitize finding text
        safe_f = "".join(c if ord(c) < 65536 else "?" for c in str(f))
        rows.append([Paragraph("●", dot_s), Paragraph(safe_f, find_s)])

    if rows:
        t = Table(rows, colWidths=[6*mm, 168*mm])
        t.setStyle(TableStyle([
            ("VALIGN",        (0,0),(-1,-1), "TOP"),
            ("TOPPADDING",    (0,0),(-1,-1), 3),
            ("BOTTOMPADDING", (0,0),(-1,-1), 3),
            ("LEFTPADDING",   (1,0),(1,-1),  4),
            ("LEFTPADDING",   (0,0),(0,-1),  0),
            ("LINEBELOW",     (0,0),(-1,-2), 0.3, C_BORDER),
        ]))
        items.append(t)
    return items


def build_footer():
    items = []
    items.append(HRFlowable(width="100%", thickness=0.5, color=C_BORDER))
    items.append(Spacer(1, 3*mm))
    footer_s = ParagraphStyle("footer", fontSize=8, fontName="Helvetica", textColor=C_GRAY, alignment=TA_CENTER, leading=11)
    disc_s   = ParagraphStyle("disc",   fontSize=7, fontName="Helvetica", textColor=C_GRAY, alignment=TA_CENTER, leading=10)
    items.append(Paragraph("Generated by <b>TruthLens</b> — AI Authenticity Detection Platform | Powered by Groq AI", footer_s))
    items.append(Spacer(1, 1*mm))
    items.append(Paragraph(
        "This report is generated by an AI system and should be used as a reference tool only. "
        "Results should be verified by qualified forensic experts before use in legal proceedings.",
        disc_s
    ))
    return items