"""Tests for /project/* API routes."""
import json


def test_project_tasks_empty(client, tmp_project_memory):
    resp = client.get('/project/tasks')
    assert resp.status_code == 200
    data = resp.json()
    assert data['tasks'] == []
    assert data['count'] == 0


def test_project_upsert_create(client, tmp_project_memory):
    payload = {
        'category': 'task',
        'taskId': 'T.01',
        'title': 'Test task',
        'status': 'not-started',
        'phase': 'P1',
        'notes': '',
    }
    resp = client.post('/project/upsert', json=payload)
    assert resp.status_code == 200
    assert resp.json()['action'] == 'created'

    # Verify persisted
    resp2 = client.get('/project/tasks')
    data = resp2.json()
    assert data['count'] == 1
    assert data['tasks'][0]['taskId'] == 'T.01'
    assert 'updatedAt' in data['tasks'][0]


def test_project_upsert_update(client, tmp_project_memory):
    payload = {
        'category': 'task',
        'taskId': 'T.02',
        'title': 'Another task',
        'status': 'not-started',
        'phase': 'P1',
        'notes': '',
    }
    client.post('/project/upsert', json=payload)

    # Update
    payload['status'] = 'completed'
    payload['notes'] = 'Done!'
    resp = client.post('/project/upsert', json=payload)
    assert resp.json()['action'] == 'updated'

    tasks = client.get('/project/tasks').json()['tasks']
    assert len(tasks) == 1
    assert tasks[0]['status'] == 'completed'
    assert tasks[0]['notes'] == 'Done!'


def test_project_summary(client, tmp_project_memory):
    for i, status in enumerate(['completed', 'completed', 'in-progress', 'not-started']):
        client.post('/project/upsert', json={
            'category': 'task',
            'taskId': f'T.{i:02d}',
            'title': f'Task {i}',
            'status': status,
            'phase': 'P1',
            'notes': '',
        })

    resp = client.get('/project/summary')
    assert resp.status_code == 200
    data = resp.json()
    assert data['total'] == 4
    assert data['completed'] == 2
    assert data['inProgress'] == 1
    assert data['notStarted'] == 1
    assert data['percentComplete'] == 50.0


def test_project_summary_ignores_non_tasks(client, tmp_project_memory):
    client.post('/project/upsert', json={
        'category': 'decision',
        'taskId': 'D.01',
        'title': 'Use Ensemble',
        'status': 'completed',
        'phase': '',
        'notes': '',
    })
    resp = client.get('/project/summary')
    assert resp.json()['total'] == 0
