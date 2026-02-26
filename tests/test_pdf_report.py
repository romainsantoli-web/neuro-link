"""Tests for /report/pdf endpoint."""


def test_pdf_report_returns_pdf(client):
    payload = {
        'status': 'AD',
        'stage': 'Modéré',
        'confidence': 0.9794,
        'features': {'alpha_power': 0.123, 'theta_ratio': 0.456},
        'report': 'Patient présente des signes compatibles avec la maladie d\'Alzheimer.',
        'pipeline': {'screening': 'AD 97.94%', 'staging': 'Modéré'},
        'patientId': 'PAT-001',
    }
    resp = client.post('/report/pdf', json=payload)
    assert resp.status_code == 200
    assert resp.headers['content-type'] == 'application/pdf'
    # PDF magic bytes
    assert resp.content[:5] == b'%PDF-'
    assert len(resp.content) > 500  # Reasonable PDF size


def test_pdf_report_minimal_payload(client):
    resp = client.post('/report/pdf', json={})
    assert resp.status_code == 200
    assert resp.content[:5] == b'%PDF-'
