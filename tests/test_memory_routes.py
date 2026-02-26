"""Tests for /memory/* API routes."""
import json


def test_memory_ingest_success(client, tmp_memory_file):
    payload = {
        'sessionId': 'sess_001',
        'fileName': 'test_file.set',
        'summary': 'EEG analysis result',
        'resultJson': '{"score": 0.95}',
    }
    resp = client.post('/memory/ingest', json=payload)
    assert resp.status_code == 200
    assert resp.json()['status'] == 'ok'

    # Verify record was stored
    records = [json.loads(l) for l in tmp_memory_file.read_text().strip().splitlines()]
    assert len(records) == 1
    assert records[0]['sessionId'] == 'sess_001'
    assert 'ingestedAt' in records[0]


def test_memory_ingest_rejects_malicious(client, tmp_memory_file):
    payload = {
        'sessionId': '../../../etc/passwd',
        'fileName': 'test.set',
        'summary': 'ok',
        'resultJson': '{}',
    }
    resp = client.post('/memory/ingest', json=payload)
    assert resp.status_code == 400


def test_memory_context_returns_results(client, tmp_memory_file):
    # Seed a record
    payload = {
        'sessionId': 'sess_002',
        'fileName': 'patient_data.set',
        'summary': 'Alzheimer detection screening',
        'resultJson': '{"class": "AD", "confidence": 0.99}',
    }
    client.post('/memory/ingest', json=payload)

    resp = client.post('/memory/context', json={
        'query': 'Alzheimer',
        'sessionId': 'sess_002',
        'limit': 5,
    })
    assert resp.status_code == 200
    data = resp.json()
    assert 'context' in data
    assert 'sourceCount' in data
