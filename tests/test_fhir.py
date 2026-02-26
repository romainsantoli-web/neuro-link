"""Tests for HL7 FHIR R4 export (P2.05)."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT_DIR))


# ═══════════ Unit tests: fhir_export module ═══════════

class TestFhirExport:

    def test_create_patient_resource(self):
        from backend.fhir_export import create_patient_resource
        patient = create_patient_resource("PAT-001", "1960-05-15")
        assert patient["resourceType"] == "Patient"
        assert patient["identifier"][0]["value"] == "PAT-001"
        assert patient["birthDate"] == "1960-05-15"
        assert patient["active"] is True

    def test_create_patient_anonymous(self):
        from backend.fhir_export import create_patient_resource
        patient = create_patient_resource()
        assert patient["identifier"][0]["value"] == "Anonyme"
        assert "birthDate" not in patient

    def test_create_observation_known_biomarker(self):
        from backend.fhir_export import create_observation_resource
        obs = create_observation_resource("Alpha", 0.35, "patient-123")
        assert obs["resourceType"] == "Observation"
        assert obs["status"] == "final"
        assert obs["code"]["text"] == "Alpha Band Power"
        assert obs["valueQuantity"]["value"] == 0.35
        assert obs["valueQuantity"]["unit"] == "µV²/Hz"
        assert obs["subject"]["reference"] == "Patient/patient-123"

    def test_create_observation_unknown_biomarker(self):
        from backend.fhir_export import create_observation_resource
        obs = create_observation_resource("CustomMetric", 42.5, "pat-999")
        assert obs["code"]["text"] == "CustomMetric"
        assert obs["valueQuantity"]["value"] == 42.5

    def test_create_diagnostic_report_alzheimer(self):
        from backend.fhir_export import create_diagnostic_report
        report = create_diagnostic_report(
            status="ALZHEIMER",
            stage="Stade 2",
            confidence=0.942,
            report_text="Test report",
            patient_ref="pat-1",
            observation_refs=["obs-1", "obs-2"],
        )
        assert report["resourceType"] == "DiagnosticReport"
        assert report["status"] == "final"
        assert "ALZHEIMER" in report["conclusion"]
        assert "94.2%" in report["conclusion"]
        assert len(report["result"]) == 2
        # Check SNOMED code for Alzheimer
        conclusion_coding = report["conclusionCode"][0]["coding"][0]
        assert conclusion_coding["code"] == "26929004"

    def test_create_diagnostic_report_normal(self):
        from backend.fhir_export import create_diagnostic_report
        report = create_diagnostic_report(
            status="NORMAL",
            stage="N/A",
            confidence=0.98,
            report_text="Tout est normal",
            patient_ref="pat-2",
            observation_refs=[],
        )
        conclusion_coding = report["conclusionCode"][0]["coding"][0]
        assert conclusion_coding["code"] == "17621005"  # Normal

    def test_create_fhir_bundle(self):
        from backend.fhir_export import create_fhir_bundle
        bundle = create_fhir_bundle(
            status="ALZHEIMER",
            stage="Stade 2 (Modéré)",
            confidence=0.942,
            features={"Alpha": 0.35, "Theta": 0.7, "Entropy": 0.82},
            report_text="Rapport détaillé ici.",
            patient_id="PAT-TEST",
        )
        assert bundle["resourceType"] == "Bundle"
        assert bundle["type"] == "document"
        # 1 Patient + 3 Observations + 1 DiagnosticReport = 5 entries
        assert len(bundle["entry"]) == 5
        assert bundle["total"] == 5

        # Check resource types
        types = [e["resource"]["resourceType"] for e in bundle["entry"]]
        assert types.count("Patient") == 1
        assert types.count("Observation") == 3
        assert types.count("DiagnosticReport") == 1

    def test_bundle_to_json(self):
        from backend.fhir_export import create_fhir_bundle, bundle_to_json
        bundle = create_fhir_bundle(
            status="NORMAL", stage="N/A", confidence=0.95,
            features={"Alpha": 0.5}, report_text="OK", patient_id="test",
        )
        json_str = bundle_to_json(bundle)
        # Should be valid JSON
        parsed = json.loads(json_str)
        assert parsed["resourceType"] == "Bundle"

    def test_validate_bundle_valid(self):
        from backend.fhir_export import create_fhir_bundle, validate_bundle_structure
        bundle = create_fhir_bundle(
            status="ALZHEIMER", stage="Stade 1", confidence=0.8,
            features={"Alpha": 0.4}, report_text="Test",
        )
        errors = validate_bundle_structure(bundle)
        assert errors == []

    def test_validate_bundle_invalid(self):
        from backend.fhir_export import validate_bundle_structure
        errors = validate_bundle_structure({"resourceType": "NotBundle", "type": "xxx", "entry": []})
        assert len(errors) > 0
        assert any("resourceType" in e for e in errors)

    def test_validate_bundle_missing_patient(self):
        from backend.fhir_export import validate_bundle_structure
        bundle = {
            "resourceType": "Bundle",
            "type": "document",
            "entry": [
                {"fullUrl": "urn:uuid:x", "resource": {"resourceType": "DiagnosticReport"}},
            ],
        }
        errors = validate_bundle_structure(bundle)
        assert any("Patient" in e for e in errors)

    def test_bundle_no_features(self):
        """Bundle with no features should still be valid (1 Patient + 1 Report)."""
        from backend.fhir_export import create_fhir_bundle, validate_bundle_structure
        bundle = create_fhir_bundle(
            status="INCONCLUSIVE", stage="Inconnu", confidence=0.0,
            features={}, report_text="Aucun résultat.",
        )
        assert len(bundle["entry"]) == 2  # Patient + DiagnosticReport
        assert validate_bundle_structure(bundle) == []


# ═══════════ Integration tests: FHIR routes ═══════════

class TestFhirRoutes:

    @pytest.fixture()
    def client(self):
        from backend.app import app
        from fastapi.testclient import TestClient
        return TestClient(app)

    def test_fhir_export_returns_bundle(self, client):
        resp = client.post("/report/fhir", json={
            "status": "ALZHEIMER",
            "stage": "Stage 2",
            "confidence": 0.94,
            "features": {"Alpha": 0.35, "Theta": 0.7},
            "report": "Test report",
            "patientId": "P-001",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["resourceType"] == "Bundle"
        assert data["type"] == "document"
        assert len(data["entry"]) == 4  # Patient + 2 Obs + 1 Report

    def test_fhir_export_minimal(self, client):
        resp = client.post("/report/fhir", json={})
        assert resp.status_code == 200
        data = resp.json()
        assert data["resourceType"] == "Bundle"

    def test_fhir_json_download(self, client):
        resp = client.post("/report/fhir/json", json={
            "status": "NORMAL",
            "stage": "N/A",
            "confidence": 0.99,
            "features": {"Alpha": 0.5},
        })
        assert resp.status_code == 200
        assert "fhir+json" in resp.headers["content-type"]
        assert "attachment" in resp.headers["content-disposition"]
        # Verify it's valid FHIR JSON
        data = resp.json()
        assert data["resourceType"] == "Bundle"
