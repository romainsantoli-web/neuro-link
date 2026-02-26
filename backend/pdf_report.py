"""PDF report generator for Neuro-Link EEG analysis results.

Uses only the Python standard library + reportlab for maximum compatibility.
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
    )

    HAS_REPORTLAB = True
except ImportError:
    HAS_REPORTLAB = False


_WIDTH, _HEIGHT = A4 if HAS_REPORTLAB else (595, 842)

DISCLAIMER_FR = (
    "AVERTISSEMENT : Neuro-Link est un outil de recherche expérimental. "
    "Il n'est PAS un dispositif médical certifié (CE/FDA). "
    "Aucun diagnostic clinique ne doit être fondé uniquement sur ces résultats. "
    "Consultez un professionnel de santé qualifié pour toute décision médicale."
)


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
        topMargin=2 * cm,
        bottomMargin=2 * cm,
    )

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'ReportTitle',
        parent=styles['Title'],
        fontSize=22,
        spaceAfter=6 * mm,
        textColor=colors.HexColor('#1e3a5f'),
    )
    heading_style = ParagraphStyle(
        'SectionHeading',
        parent=styles['Heading2'],
        fontSize=14,
        spaceAfter=3 * mm,
        textColor=colors.HexColor('#1e3a5f'),
    )
    body_style = styles['BodyText']
    disclaimer_style = ParagraphStyle(
        'Disclaimer',
        parent=body_style,
        fontSize=8,
        textColor=colors.grey,
        spaceBefore=10 * mm,
    )

    elements: list = []

    # ── Title ──
    elements.append(Paragraph('Neuro-Link — Rapport EEG', title_style))
    elements.append(Spacer(1, 4 * mm))

    # ── Metadata table ──
    now = datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')
    meta_data = [
        ['Patient', patient_id],
        ['Date du rapport', now],
        ['Statut', analysis.get('status', 'N/A')],
        ['Stade', analysis.get('stage', 'N/A')],
        ['Confiance', f"{float(analysis.get('confidence', 0)) * 100:.2f} %"],
    ]
    meta_table = Table(meta_data, colWidths=[5 * cm, 10 * cm])
    meta_table.setStyle(
        TableStyle(
            [
                ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#e8eef5')),
                ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.lightgrey),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('TOPPADDING', (0, 0), (-1, -1), 4),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
            ]
        )
    )
    elements.append(meta_table)
    elements.append(Spacer(1, 8 * mm))

    # ── Narrative report ──
    report_text = analysis.get('report', '')
    if report_text:
        elements.append(Paragraph('Rapport narratif', heading_style))
        for paragraph in report_text.split('\n'):
            if paragraph.strip():
                elements.append(Paragraph(paragraph.strip(), body_style))
                elements.append(Spacer(1, 2 * mm))
        elements.append(Spacer(1, 4 * mm))

    # ── Features table ──
    features: dict = analysis.get('features', {})
    if features:
        elements.append(Paragraph('Caractéristiques extraites', heading_style))
        feat_rows = [['Caractéristique', 'Valeur']]
        for key, val in features.items():
            display_val = f'{val:.6f}' if isinstance(val, float) else str(val)
            feat_rows.append([key, display_val])

        feat_table = Table(feat_rows, colWidths=[8 * cm, 7 * cm])
        feat_table.setStyle(
            TableStyle(
                [
                    ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1e3a5f')),
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                    ('GRID', (0, 0), (-1, -1), 0.5, colors.lightgrey),
                    ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f5f7fa')]),
                    ('TOPPADDING', (0, 0), (-1, -1), 3),
                    ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
                ]
            )
        )
        elements.append(feat_table)
        elements.append(Spacer(1, 6 * mm))

    # ── Pipeline info ──
    pipeline: dict = analysis.get('pipeline', {})
    if pipeline:
        elements.append(Paragraph('Pipeline', heading_style))
        pipe_rows = [['Étape', 'Détail']]
        for key, val in pipeline.items():
            pipe_rows.append([key, str(val)])
        pipe_table = Table(pipe_rows, colWidths=[5 * cm, 10 * cm])
        pipe_table.setStyle(
            TableStyle(
                [
                    ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1e3a5f')),
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                    ('GRID', (0, 0), (-1, -1), 0.5, colors.lightgrey),
                    ('TOPPADDING', (0, 0), (-1, -1), 3),
                    ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
                ]
            )
        )
        elements.append(pipe_table)

    # ── Disclaimer ──
    elements.append(Spacer(1, 10 * mm))
    elements.append(Paragraph(DISCLAIMER_FR, disclaimer_style))

    doc.build(elements)
    pdf_bytes = buf.getvalue()
    buf.close()
    return pdf_bytes
