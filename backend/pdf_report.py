"""PDF report generator for Neuro-Link EEG analysis results.

Produces a professional, medical-grade PDF with branded header/footer,
structured sections, and clean typography using reportlab.
"""
from __future__ import annotations

import io
from datetime import datetime
from typing import Any

try:
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.lib.units import cm, mm
    from reportlab.platypus import (
        Paragraph,
        SimpleDocTemplate,
        Spacer,
        Table,
        TableStyle,
        HRFlowable,
        KeepTogether,
    )
    from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_JUSTIFY

    HAS_REPORTLAB = True
except ImportError:
    HAS_REPORTLAB = False


_WIDTH, _HEIGHT = A4 if HAS_REPORTLAB else (595, 842)

# ── Brand Colors ──
_BRAND_DARK = colors.HexColor('#0a1628')
_BRAND_CYAN = colors.HexColor('#00b8a9')
_BRAND_PURPLE = colors.HexColor('#7c3aed')
_BRAND_HEADING = colors.HexColor('#1a2744')
_BRAND_TEXT = colors.HexColor('#334155')
_BRAND_LIGHT_BG = colors.HexColor('#f8fafc')
_BRAND_BORDER = colors.HexColor('#e2e8f0')
_BRAND_ACCENT_BG = colors.HexColor('#f0f9ff')
_BRAND_RED = colors.HexColor('#dc2626')
_BRAND_GREEN = colors.HexColor('#059669')

DISCLAIMER_FR = (
    "AVERTISSEMENT — Neuro-Link est un outil de recherche expérimental. "
    "Il n'est PAS un dispositif médical certifié (CE/FDA). "
    "Aucun diagnostic clinique ne doit être fondé uniquement sur ces résultats. "
    "Consultez un professionnel de santé qualifié pour toute décision médicale."
)


def _build_header_footer(canvas, doc):
    """Draw branded header and footer on every page."""
    canvas.saveState()
    width = _WIDTH

    # ── Header ──
    # Top accent line
    canvas.setStrokeColor(_BRAND_CYAN)
    canvas.setLineWidth(3)
    canvas.line(0, _HEIGHT - 12 * mm, width, _HEIGHT - 12 * mm)

    # Brand name
    canvas.setFont('Helvetica-Bold', 16)
    canvas.setFillColor(_BRAND_HEADING)
    canvas.drawString(2 * cm, _HEIGHT - 20 * mm, 'NEURO-LINK')

    # Version badge
    canvas.setFont('Helvetica', 8)
    canvas.setFillColor(_BRAND_CYAN)
    canvas.drawString(2 * cm + 108, _HEIGHT - 20 * mm + 1, 'v18.0')

    # Subtitle
    canvas.setFont('Helvetica', 8)
    canvas.setFillColor(_BRAND_TEXT)
    canvas.drawString(2 * cm, _HEIGHT - 25 * mm, 'Rapport d\'Analyse EEG — Dépistage Alzheimer')

    # Right-side info
    canvas.setFont('Helvetica', 7)
    canvas.setFillColor(colors.HexColor('#94a3b8'))
    now = datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')
    canvas.drawRightString(width - 2 * cm, _HEIGHT - 20 * mm, now)
    canvas.drawRightString(width - 2 * cm, _HEIGHT - 25 * mm, f'Page {doc.page}')

    # Header separator
    canvas.setStrokeColor(_BRAND_BORDER)
    canvas.setLineWidth(0.5)
    canvas.line(2 * cm, _HEIGHT - 28 * mm, width - 2 * cm, _HEIGHT - 28 * mm)

    # ── Footer ──
    canvas.setStrokeColor(_BRAND_BORDER)
    canvas.setLineWidth(0.5)
    canvas.line(2 * cm, 18 * mm, width - 2 * cm, 18 * mm)

    canvas.setFont('Helvetica', 6)
    canvas.setFillColor(colors.HexColor('#94a3b8'))
    canvas.drawString(2 * cm, 13 * mm, 'NEURO-LINK v18.0 — Outil de recherche expérimental — Non certifié CE/FDA')
    canvas.drawRightString(width - 2 * cm, 13 * mm, 'Document confidentiel')

    # Bottom accent line
    canvas.setStrokeColor(_BRAND_CYAN)
    canvas.setLineWidth(2)
    canvas.line(0, 8 * mm, width, 8 * mm)

    canvas.restoreState()


def generate_pdf_report(analysis: dict[str, Any], patient_id: str = 'Anonyme') -> bytes:
    """Generate a professional PDF report from analysis results.

    Parameters
    ----------
    analysis : dict
        The /analyze endpoint response payload.
    patient_id : str
        An optional patient identifier shown in the header.

    Returns
    -------
    bytes
        Raw PDF bytes ready to stream back to the client.
    """
    if not HAS_REPORTLAB:
        raise RuntimeError('reportlab is not installed — run: pip install reportlab')

    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=A4,
        leftMargin=2 * cm,
        rightMargin=2 * cm,
        topMargin=3.5 * cm,
        bottomMargin=2.5 * cm,
    )

    styles = getSampleStyleSheet()

    # ── Custom Styles ──
    title_style = ParagraphStyle(
        'NLTitle',
        parent=styles['Title'],
        fontSize=20,
        fontName='Helvetica-Bold',
        spaceAfter=4 * mm,
        textColor=_BRAND_HEADING,
        alignment=TA_CENTER,
        leading=26,
    )
    section_style = ParagraphStyle(
        'NLSection',
        parent=styles['Heading2'],
        fontSize=13,
        fontName='Helvetica-Bold',
        spaceBefore=8 * mm,
        spaceAfter=3 * mm,
        textColor=_BRAND_HEADING,
        borderPadding=(0, 0, 2, 0),
    )
    body_style = ParagraphStyle(
        'NLBody',
        parent=styles['BodyText'],
        fontSize=10,
        fontName='Helvetica',
        textColor=_BRAND_TEXT,
        leading=15,
        alignment=TA_JUSTIFY,
        spaceAfter=2 * mm,
    )
    body_bold = ParagraphStyle(
        'NLBodyBold',
        parent=body_style,
        fontName='Helvetica-Bold',
        textColor=_BRAND_HEADING,
    )
    caption_style = ParagraphStyle(
        'NLCaption',
        parent=styles['Normal'],
        fontSize=7,
        fontName='Helvetica',
        textColor=colors.HexColor('#94a3b8'),
        alignment=TA_CENTER,
        spaceBefore=2 * mm,
    )
    disclaimer_style = ParagraphStyle(
        'NLDisclaimer',
        parent=body_style,
        fontSize=7,
        fontName='Helvetica-Oblique',
        textColor=colors.HexColor('#94a3b8'),
        spaceBefore=10 * mm,
        alignment=TA_LEFT,
        leading=10,
        borderWidth=0.5,
        borderColor=colors.HexColor('#e2e8f0'),
        borderPadding=8,
        backColor=colors.HexColor('#fafafa'),
    )
    status_positive = ParagraphStyle(
        'StatusPos',
        parent=title_style,
        fontSize=18,
        textColor=_BRAND_RED,
    )
    status_negative = ParagraphStyle(
        'StatusNeg',
        parent=title_style,
        fontSize=18,
        textColor=_BRAND_GREEN,
    )

    elements: list = []

    # ── Title ──
    elements.append(Spacer(1, 2 * mm))
    elements.append(Paragraph('Rapport d\'Analyse EEG', title_style))
    elements.append(Paragraph(
        '<font size="9" color="#94a3b8">Système d\'aide au dépistage de la maladie d\'Alzheimer</font>',
        ParagraphStyle('Subtitle', parent=title_style, fontSize=9, textColor=colors.HexColor('#94a3b8'))
    ))
    elements.append(Spacer(1, 4 * mm))

    # Thin cyan line under title
    elements.append(HRFlowable(
        width='40%', thickness=2, color=_BRAND_CYAN,
        spaceAfter=6 * mm, spaceBefore=0, hAlign='CENTER'
    ))

    # ── Metadata Card ──
    now = datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')
    status_val = analysis.get('status', 'N/A')
    confidence = float(analysis.get('confidence', 0))
    stage = analysis.get('stage', 'N/A')

    meta_data = [
        ['Patient', patient_id, 'Date', now],
        ['Statut', status_val, 'Stade', stage],
        ['Confiance', f'{confidence * 100:.1f} %', 'Version', 'Neuro-Link v18.0'],
    ]
    meta_table = Table(meta_data, colWidths=[3.5 * cm, 4.5 * cm, 3.5 * cm, 4.5 * cm])

    # Determine status color for the table
    status_bg = colors.HexColor('#fef2f2') if 'ALZHEIMER' in str(status_val).upper() else colors.HexColor('#f0fdf4')
    status_text = _BRAND_RED if 'ALZHEIMER' in str(status_val).upper() else _BRAND_GREEN

    meta_style = [
        # Header columns
        ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#f1f5f9')),
        ('BACKGROUND', (2, 0), (2, -1), colors.HexColor('#f1f5f9')),
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTNAME', (2, 0), (2, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('TEXTCOLOR', (0, 0), (0, -1), _BRAND_HEADING),
        ('TEXTCOLOR', (2, 0), (2, -1), _BRAND_HEADING),
        ('TEXTCOLOR', (1, 0), (1, -1), _BRAND_TEXT),
        ('TEXTCOLOR', (3, 0), (3, -1), _BRAND_TEXT),
        # Status row highlight
        ('BACKGROUND', (1, 1), (1, 1), status_bg),
        ('TEXTCOLOR', (1, 1), (1, 1), status_text),
        ('FONTNAME', (1, 1), (1, 1), 'Helvetica-Bold'),
        # Grid
        ('GRID', (0, 0), (-1, -1), 0.5, _BRAND_BORDER),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('LEFTPADDING', (0, 0), (-1, -1), 8),
        ('ROUNDEDCORNERS', [3, 3, 3, 3]),
    ]
    meta_table.setStyle(TableStyle(meta_style))
    elements.append(meta_table)
    elements.append(Spacer(1, 8 * mm))

    # ── Narrative Report ──
    report_text = analysis.get('report', '')
    if report_text:
        elements.append(Paragraph('Rapport Narratif', section_style))
        elements.append(HRFlowable(
            width='100%', thickness=0.5, color=_BRAND_BORDER,
            spaceAfter=4 * mm, spaceBefore=0
        ))
        for paragraph in report_text.split('\n'):
            stripped = paragraph.strip()
            if not stripped:
                elements.append(Spacer(1, 2 * mm))
                continue
            # Clean markdown markers for PDF
            cleaned = stripped.replace('[IMAGE_XAI]', '').replace('[IMAGE_QR]', '')
            if cleaned.startswith('###'):
                cleaned = cleaned.replace('###', '').strip().replace('**', '')
                elements.append(Spacer(1, 3 * mm))
                elements.append(Paragraph(cleaned, ParagraphStyle(
                    'SubSection', parent=section_style, fontSize=11,
                    textColor=_BRAND_CYAN, spaceBefore=4 * mm
                )))
            elif cleaned.startswith('**') and cleaned.endswith('**'):
                cleaned = cleaned.replace('**', '')
                elements.append(Paragraph(cleaned, body_bold))
            elif cleaned.startswith('* '):
                cleaned = cleaned[2:]
                # Bullet with styled text
                cleaned = cleaned.replace('**', '<b>').replace('**', '</b>')
                elements.append(Paragraph(f'• {cleaned}', body_style))
            elif cleaned.startswith('---'):
                elements.append(HRFlowable(
                    width='100%', thickness=0.3, color=_BRAND_BORDER,
                    spaceAfter=3 * mm, spaceBefore=3 * mm
                ))
            elif cleaned:
                # Replace markdown bold **text** with XML bold
                import re
                cleaned = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', cleaned)
                elements.append(Paragraph(cleaned, body_style))

        elements.append(Spacer(1, 4 * mm))

    # ── Features Table ──
    features: dict = analysis.get('features', {})
    if features:
        elements.append(Paragraph('Caractéristiques Spectrales Extraites', section_style))
        elements.append(HRFlowable(
            width='100%', thickness=0.5, color=_BRAND_BORDER,
            spaceAfter=4 * mm, spaceBefore=0
        ))

        feat_rows = [['Caractéristique', 'Valeur', 'Unité']]
        for key, val in features.items():
            display_val = f'{val:.6f}' if isinstance(val, float) else str(val)
            unit = 'µV²/Hz' if 'power' in key.lower() or key.lower() in ('alpha', 'theta', 'delta', 'beta') else 'a.u.'
            feat_rows.append([key, display_val, unit])

        feat_table = Table(feat_rows, colWidths=[6 * cm, 5 * cm, 5 * cm])
        feat_table.setStyle(
            TableStyle(
                [
                    ('BACKGROUND', (0, 0), (-1, 0), _BRAND_HEADING),
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                    ('FONTSIZE', (0, 0), (-1, 0), 9),
                    ('FONTSIZE', (0, 1), (-1, -1), 9),
                    ('FONTNAME', (1, 1), (1, -1), 'Courier'),
                    ('GRID', (0, 0), (-1, -1), 0.5, _BRAND_BORDER),
                    ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, _BRAND_LIGHT_BG]),
                    ('TOPPADDING', (0, 0), (-1, -1), 5),
                    ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
                    ('LEFTPADDING', (0, 0), (-1, -1), 8),
                    ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                    ('ALIGN', (1, 0), (2, -1), 'CENTER'),
                ]
            )
        )
        elements.append(feat_table)
        elements.append(Spacer(1, 6 * mm))

    # ── Pipeline Info ──
    pipeline: dict = analysis.get('pipeline', {})
    if pipeline:
        elements.append(Paragraph('Pipeline d\'Analyse', section_style))
        elements.append(HRFlowable(
            width='100%', thickness=0.5, color=_BRAND_BORDER,
            spaceAfter=4 * mm, spaceBefore=0
        ))
        pipe_rows = [['Étape', 'Détail']]
        for key, val in pipeline.items():
            pipe_rows.append([key, str(val)])
        pipe_table = Table(pipe_rows, colWidths=[5 * cm, 11 * cm])
        pipe_table.setStyle(
            TableStyle(
                [
                    ('BACKGROUND', (0, 0), (-1, 0), _BRAND_HEADING),
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                    ('FONTSIZE', (0, 0), (-1, -1), 9),
                    ('GRID', (0, 0), (-1, -1), 0.5, _BRAND_BORDER),
                    ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, _BRAND_LIGHT_BG]),
                    ('TOPPADDING', (0, 0), (-1, -1), 5),
                    ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
                    ('LEFTPADDING', (0, 0), (-1, -1), 8),
                ]
            )
        )
        elements.append(pipe_table)

    # ── Disclaimer ──
    elements.append(Spacer(1, 8 * mm))
    elements.append(Paragraph(DISCLAIMER_FR, disclaimer_style))

    doc.build(elements, onFirstPage=_build_header_footer, onLaterPages=_build_header_footer)
    pdf_bytes = buf.getvalue()
    buf.close()
    return pdf_bytes
