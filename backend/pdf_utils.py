"""PDF generation utilities for SIPRO documents (Phase F1).

Uses reportlab.platypus to render markdown-lite content into A4 PDF.
Supported lightweight formatting:
  - Lines starting with `# ` → H1 (24pt bold center)
  - Lines starting with `## ` → H2 (16pt bold)
  - Lines starting with `### ` → H3 (12pt bold)
  - Lines starting with `- ` → bullet list item
  - `**bold**` inline → bold text
  - Blank line → paragraph break
"""
import io
import re
from datetime import datetime
from typing import Optional

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, Image as RLImage,
)
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_LEFT


def _build_styles():
    base = getSampleStyleSheet()
    styles = {
        "h1": ParagraphStyle("h1", parent=base["Title"], fontName="Helvetica-Bold", fontSize=18, alignment=TA_CENTER, spaceAfter=8, leading=22),
        "h2": ParagraphStyle("h2", parent=base["Heading2"], fontName="Helvetica-Bold", fontSize=13, spaceBefore=12, spaceAfter=6, leading=16),
        "h3": ParagraphStyle("h3", parent=base["Heading3"], fontName="Helvetica-Bold", fontSize=11, spaceBefore=8, spaceAfter=4, leading=14),
        "body": ParagraphStyle("body", parent=base["Normal"], fontName="Helvetica", fontSize=10, alignment=TA_JUSTIFY, leading=14, spaceAfter=4),
        "bullet": ParagraphStyle("bullet", parent=base["Normal"], fontName="Helvetica", fontSize=10, leftIndent=14, bulletIndent=4, leading=14, spaceAfter=2),
        "small": ParagraphStyle("small", parent=base["Normal"], fontName="Helvetica", fontSize=8, textColor=colors.grey, alignment=TA_CENTER),
        "sign_label": ParagraphStyle("sign_label", parent=base["Normal"], fontName="Helvetica-Bold", fontSize=9, alignment=TA_CENTER),
        "sign_name": ParagraphStyle("sign_name", parent=base["Normal"], fontName="Helvetica-Bold", fontSize=10, alignment=TA_CENTER),
    }
    return styles


def _inline_format(text: str) -> str:
    """Apply lightweight inline formatting → reportlab paragraph markup.

    Escapes XML, then converts **bold** to <b>bold</b>.
    """
    # XML-escape first
    text = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    # Then bold
    text = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", text)
    return text


def render_content_to_flowables(content: str, styles: dict):
    """Convert markdown-lite content into reportlab flowables."""
    flowables = []
    lines = content.split("\n")
    para_buffer = []

    def flush_paragraph():
        if para_buffer:
            text = " ".join(para_buffer).strip()
            if text:
                flowables.append(Paragraph(_inline_format(text), styles["body"]))
            para_buffer.clear()

    for ln in lines:
        s = ln.rstrip()
        if not s.strip():
            flush_paragraph()
            flowables.append(Spacer(1, 4))
            continue
        if s.startswith("# "):
            flush_paragraph()
            flowables.append(Paragraph(_inline_format(s[2:]), styles["h1"]))
            continue
        if s.startswith("## "):
            flush_paragraph()
            flowables.append(Paragraph(_inline_format(s[3:]), styles["h2"]))
            continue
        if s.startswith("### "):
            flush_paragraph()
            flowables.append(Paragraph(_inline_format(s[4:]), styles["h3"]))
            continue
        if s.startswith("- "):
            flush_paragraph()
            flowables.append(Paragraph(_inline_format(s[2:]), styles["bullet"], bulletText="•"))
            continue
        # Regular line — accumulate into paragraph buffer
        para_buffer.append(s)
    flush_paragraph()
    return flowables


def _signature_table(signatures: list, styles: dict):
    """Build a signature panel at the bottom of the document."""
    if not signatures:
        return None
    cells = []
    for sig in signatures:
        role_label = {"buyer": "Pembeli", "seller": "Penjual", "witness": "Saksi"}.get(sig.get("role", "").lower(), sig.get("role", "").title())
        signed_at = sig.get("signed_at", "")
        try:
            dt = datetime.fromisoformat(signed_at.replace("Z", "+00:00"))
            signed_str = dt.strftime("%d %b %Y %H:%M")
        except Exception:
            signed_str = signed_at[:16] if signed_at else "-"
        sig_img = None
        sig_data = sig.get("signature_image", "")
        if sig_data and sig_data.startswith("data:image"):
            try:
                _, b64 = sig_data.split(",", 1)
                import base64
                img_bytes = base64.b64decode(b64)
                sig_img = RLImage(io.BytesIO(img_bytes), width=50*mm, height=20*mm, kind="proportional")
            except Exception:
                sig_img = Paragraph("(tanda tangan)", styles["small"])
        else:
            sig_img = Paragraph("(belum ditandatangani)", styles["small"])
        cell = [
            Paragraph(role_label, styles["sign_label"]),
            Spacer(1, 4),
            sig_img,
            Spacer(1, 4),
            Paragraph(sig.get("name", "-"), styles["sign_name"]),
            Paragraph(f"Ditandatangani: {signed_str}", styles["small"]),
        ]
        cells.append(cell)

    # Up to 3 signatures per row
    rows = []
    while cells:
        row = cells[:3]
        cells = cells[3:]
        while len(row) < 3:
            row.append([])
        rows.append(row)
    tbl = Table(rows, colWidths=[60*mm, 60*mm, 60*mm])
    tbl.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("TOPPADDING", (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
    ]))
    return tbl


def build_document_pdf(*, title: str, content: str, signatures: list = None, doc_code: str = "", doc_number: str = "") -> bytes:
    """Render a document into PDF bytes. Returns the binary PDF content."""
    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=A4,
        leftMargin=20*mm, rightMargin=20*mm, topMargin=20*mm, bottomMargin=20*mm,
        title=title or "Document",
    )
    styles = _build_styles()

    flowables = []
    # Header: doc code + number
    if doc_code or doc_number:
        flowables.append(Paragraph(f"<b>{doc_code}</b> &nbsp; {doc_number}", styles["small"]))
        flowables.append(Spacer(1, 6))
    flowables.extend(render_content_to_flowables(content, styles))

    # Signature panel
    if signatures:
        flowables.append(Spacer(1, 18))
        sig_tbl = _signature_table(signatures, styles)
        if sig_tbl is not None:
            flowables.append(sig_tbl)

    # Footer note
    flowables.append(Spacer(1, 12))
    footer = f"Dokumen ini dihasilkan secara elektronik oleh SIPRO pada {datetime.now().strftime('%d %B %Y %H:%M')}."
    flowables.append(Paragraph(footer, styles["small"]))

    doc.build(flowables)
    pdf_bytes = buf.getvalue()
    buf.close()
    return pdf_bytes


# ---- Variable resolution ----
VAR_RE = re.compile(r"\{\{\s*([\w.]+)\s*\}\}")


def _idr_words(n: float) -> str:
    """Convert number to Indonesian words (limited; covers up to triliun). Simple implementation."""
    n = int(round(n))
    if n == 0:
        return "nol"
    satuan = ["", "satu", "dua", "tiga", "empat", "lima", "enam", "tujuh", "delapan", "sembilan", "sepuluh", "sebelas"]

    def _three(num):
        if num == 0:
            return ""
        if num < 12:
            return satuan[num]
        if num < 20:
            return _three(num - 10) + " belas"
        if num < 100:
            return satuan[num // 10] + " puluh" + (" " + _three(num % 10) if num % 10 else "")
        if num < 200:
            return "seratus" + (" " + _three(num - 100) if num > 100 else "")
        if num < 1000:
            return satuan[num // 100] + " ratus" + (" " + _three(num % 100) if num % 100 else "")
        return ""

    def _convert(num):
        if num == 0:
            return ""
        parts = []
        triliun = num // 1_000_000_000_000
        if triliun:
            parts.append(_three(triliun) + " triliun")
            num %= 1_000_000_000_000
        milyar = num // 1_000_000_000
        if milyar:
            parts.append(_three(milyar) + " milyar")
            num %= 1_000_000_000
        juta = num // 1_000_000
        if juta:
            parts.append(_three(juta) + " juta")
            num %= 1_000_000
        ribu = num // 1000
        if ribu:
            parts.append(("seribu" if ribu == 1 else _three(ribu) + " ribu"))
            num %= 1000
        if num:
            parts.append(_three(num))
        return " ".join(p for p in parts if p)

    return _convert(n).strip() + " rupiah"


def _fmt_idr(n) -> str:
    try:
        return "Rp " + f"{float(n):,.0f}".replace(",", ".")
    except Exception:
        return str(n or "")


def _fmt_date(s: Optional[str]) -> str:
    if not s:
        return "-"
    try:
        dt = datetime.fromisoformat(str(s).replace("Z", "+00:00"))
        bulan = ["", "Januari", "Februari", "Maret", "April", "Mei", "Juni", "Juli", "Agustus", "September", "Oktober", "November", "Desember"]
        return f"{dt.day} {bulan[dt.month]} {dt.year}"
    except Exception:
        return s[:10]


def resolve_variables(content: str, context: dict) -> str:
    """Replace {{path.to.field}} with values from context dict.

    Special suffixes supported:
      - {{deal.price_idr}}    → "Rp 500.000.000"
      - {{deal.price_words}}  → "lima ratus juta rupiah"
      - {{today}}             → today formatted Indonesian
      - {{today.iso}}         → ISO date today
    """
    today = datetime.now()
    bulan = ["", "Januari", "Februari", "Maret", "April", "Mei", "Juni", "Juli", "Agustus", "September", "Oktober", "November", "Desember"]
    extras = {
        "today": f"{today.day} {bulan[today.month]} {today.year}",
        "today.iso": today.strftime("%Y-%m-%d"),
    }

    def resolver(match):
        path = match.group(1)
        if path in extras:
            return extras[path]
        # Look up dotted path in context
        cur = context
        for part in path.split("."):
            if isinstance(cur, dict):
                cur = cur.get(part)
            else:
                cur = None
                break
        # Special formatters on terminal value
        if path.endswith(".price_idr") or path.endswith(".amount_idr"):
            base = path.rsplit(".", 1)[0]
            val = _resolve_path(context, base)
            return _fmt_idr(val)
        if path.endswith(".price_words") or path.endswith(".amount_words"):
            base = path.rsplit(".", 1)[0]
            val = _resolve_path(context, base)
            try:
                return _idr_words(float(val))
            except Exception:
                return "-"
        if path.endswith(".date_id"):
            base = path.rsplit(".", 1)[0]
            val = _resolve_path(context, base)
            return _fmt_date(val)
        if cur is None or cur == "":
            return "_______________"
        return str(cur)

    return VAR_RE.sub(resolver, content)


def _resolve_path(context: dict, path: str):
    cur = context
    for part in path.split("."):
        if isinstance(cur, dict):
            cur = cur.get(part)
        else:
            return None
    return cur
