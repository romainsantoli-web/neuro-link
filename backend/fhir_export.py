"""
HL7 FHIR integration for Neuro-Link.

Provides:
- DiagnosticReport resource generation from analysis results
- Patient resource handling
- Observation resources for EEG biomarkers
- FHIR Bundle creation for complete reports
- Export in JSON (FHIR R4) format

Follows HL7 FHIR R4 specification:
  https://www.hl7.org/fhir/R4/

Resources generated:
  - DiagnosticReport: Main analysis result
  - Observation: Individual biomarker measurements (Alpha, Theta, Entropy, etc.)
  - Patient: Anonymized patient reference
  - Bundle: Collection of all resources (type=document)
"""

from __future__ import annotations

import hashlib
import json
import uuid
from datetime import datetime, timezone
from typing import Any


FHIR_BASE_URL = "https://neuro-link.ai/fhir"
LOINC_EEG = "11524-6"  # EEG study (LOINC)
SNOMED_ALZHEIMER = "26929004"  # Alzheimer's disease (SNOMED CT)
SNOMED_EEG = "54550000"  # Electroencephalography (SNOMED CT)


def _uuid() -> str:
    return str(uuid.uuid4())


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S+00:00")


# ── Patient Resource ──────────────────────────────────────────

def create_patient_resource(patient_id: str = "Anonyme", birth_date: str = "") -> dict[str, Any]:
    """
    Create a FHIR Patient resource.

    For privacy, only minimal identifiers are included.
    """
    resource: dict[str, Any] = {
        "resourceType": "Patient",
        "id": _uuid(),
        "meta": {
            "profile": ["http://hl7.org/fhir/StructureDefinition/Patient"],
        },
        "identifier": [
            {
                "system": f"{FHIR_BASE_URL}/patient-id",
                "value": patient_id,
            }
        ],
        "active": True,
    }

    if birth_date:
        resource["birthDate"] = birth_date

    return resource


# ── Observation Resources (Biomarkers) ─────────────────────────

# Mapping of feature names to FHIR-compatible display names and units
BIOMARKER_MAP: dict[str, dict[str, str]] = {
    "Alpha": {"display": "Alpha Band Power", "unit": "µV²/Hz", "code": "brain-alpha"},
    "Theta": {"display": "Theta Band Power", "unit": "µV²/Hz", "code": "brain-theta"},
    "Beta": {"display": "Beta Band Power", "unit": "µV²/Hz", "code": "brain-beta"},
    "Delta": {"display": "Delta Band Power", "unit": "µV²/Hz", "code": "brain-delta"},
    "Gamma": {"display": "Gamma Band Power", "unit": "µV²/Hz", "code": "brain-gamma"},
    "Entropy": {"display": "Signal Entropy", "unit": "{entropy}", "code": "signal-entropy"},
    "Complexity": {"display": "Signal Complexity", "unit": "{index}", "code": "signal-complexity"},
    "Coherence": {"display": "Inter-channel Coherence", "unit": "{ratio}", "code": "coherence"},
}


def create_observation_resource(
    feature_name: str,
    value: float,
    patient_ref: str,
    effective_time: str | None = None,
) -> dict[str, Any]:
    """Create a FHIR Observation resource for a single EEG biomarker."""
    bio = BIOMARKER_MAP.get(feature_name, {
        "display": feature_name,
        "unit": "{value}",
        "code": feature_name.lower().replace(" ", "-"),
    })

    return {
        "resourceType": "Observation",
        "id": _uuid(),
        "meta": {
            "profile": ["http://hl7.org/fhir/StructureDefinition/Observation"],
        },
        "status": "final",
        "category": [
            {
                "coding": [
                    {
                        "system": "http://terminology.hl7.org/CodeSystem/observation-category",
                        "code": "procedure",
                        "display": "Procedure",
                    }
                ]
            }
        ],
        "code": {
            "coding": [
                {
                    "system": f"{FHIR_BASE_URL}/biomarker",
                    "code": bio["code"],
                    "display": bio["display"],
                }
            ],
            "text": bio["display"],
        },
        "subject": {"reference": f"Patient/{patient_ref}"},
        "effectiveDateTime": effective_time or _now_iso(),
        "valueQuantity": {
            "value": round(value, 6),
            "unit": bio["unit"],
            "system": "http://unitsofmeasure.org",
        },
    }


# ── DiagnosticReport Resource ──────────────────────────────────

def create_diagnostic_report(
    status: str,
    stage: str,
    confidence: float,
    report_text: str,
    patient_ref: str,
    observation_refs: list[str],
    effective_time: str | None = None,
) -> dict[str, Any]:
    """Create a FHIR DiagnosticReport resource for the EEG analysis."""
    effective = effective_time or _now_iso()

    # Map our status to FHIR conclusion codes
    conclusion_code = {
        "ALZHEIMER": {"code": SNOMED_ALZHEIMER, "display": "Alzheimer's disease"},
        "NORMAL": {"code": "17621005", "display": "Normal (finding)"},
        "INCONCLUSIVE": {"code": "419984006", "display": "Inconclusive (qualifier value)"},
    }.get(status, {"code": "419984006", "display": "Inconclusive"})

    return {
        "resourceType": "DiagnosticReport",
        "id": _uuid(),
        "meta": {
            "profile": ["http://hl7.org/fhir/StructureDefinition/DiagnosticReport"],
        },
        "status": "final",
        "category": [
            {
                "coding": [
                    {
                        "system": "http://terminology.hl7.org/CodeSystem/v2-0074",
                        "code": "NRS",
                        "display": "Neurology",
                    }
                ]
            }
        ],
        "code": {
            "coding": [
                {
                    "system": "http://loinc.org",
                    "code": LOINC_EEG,
                    "display": "EEG study",
                },
                {
                    "system": "http://snomed.info/sct",
                    "code": SNOMED_EEG,
                    "display": "Electroencephalography",
                },
            ],
            "text": "Neuro-Link EEG Analysis — Alzheimer Screening",
        },
        "subject": {"reference": f"Patient/{patient_ref}"},
        "effectiveDateTime": effective,
        "issued": _now_iso(),
        "result": [{"reference": f"Observation/{ref}"} for ref in observation_refs],
        "conclusion": f"Statut: {status} | Stade: {stage} | Confiance: {confidence:.1%}",
        "conclusionCode": [
            {
                "coding": [
                    {
                        "system": "http://snomed.info/sct",
                        **conclusion_code,
                    }
                ]
            }
        ],
        "presentedForm": [
            {
                "contentType": "text/plain",
                "data": None,  # Will be base64-encoded if needed
                "title": "Rapport d'analyse Neuro-Link",
            }
        ],
        "extension": [
            {
                "url": f"{FHIR_BASE_URL}/extension/confidence",
                "valueDecimal": round(confidence, 4),
            },
            {
                "url": f"{FHIR_BASE_URL}/extension/stage",
                "valueString": stage,
            },
        ],
    }


# ── Bundle Generator ──────────────────────────────────────────

def create_fhir_bundle(
    status: str,
    stage: str,
    confidence: float,
    features: dict[str, float],
    report_text: str,
    patient_id: str = "Anonyme",
) -> dict[str, Any]:
    """
    Create a complete FHIR Bundle (type=document) containing:
    - Patient
    - Observations (one per biomarker)
    - DiagnosticReport

    Returns a FHIR R4 Bundle as a Python dict.
    """
    effective_time = _now_iso()

    # 1. Patient
    patient = create_patient_resource(patient_id)
    patient_ref = patient["id"]

    # 2. Observations
    observations = []
    for name, value in features.items():
        obs = create_observation_resource(
            feature_name=name,
            value=float(value),
            patient_ref=patient_ref,
            effective_time=effective_time,
        )
        observations.append(obs)

    observation_refs = [obs["id"] for obs in observations]

    # 3. DiagnosticReport
    report = create_diagnostic_report(
        status=status,
        stage=stage,
        confidence=confidence,
        report_text=report_text,
        patient_ref=patient_ref,
        observation_refs=observation_refs,
        effective_time=effective_time,
    )

    # 4. Bundle
    entries = [
        {"fullUrl": f"urn:uuid:{patient['id']}", "resource": patient},
        *[{"fullUrl": f"urn:uuid:{obs['id']}", "resource": obs} for obs in observations],
        {"fullUrl": f"urn:uuid:{report['id']}", "resource": report},
    ]

    bundle: dict[str, Any] = {
        "resourceType": "Bundle",
        "id": _uuid(),
        "meta": {
            "lastUpdated": _now_iso(),
        },
        "type": "document",
        "timestamp": effective_time,
        "entry": entries,
        "total": len(entries),
    }

    return bundle


def bundle_to_json(bundle: dict[str, Any], indent: int = 2) -> str:
    """Serialize a FHIR Bundle to JSON string."""
    return json.dumps(bundle, ensure_ascii=False, indent=indent)


def validate_bundle_structure(bundle: dict[str, Any]) -> list[str]:
    """
    Basic structural validation of a FHIR Bundle.

    Returns list of validation errors (empty = valid).
    """
    errors: list[str] = []

    if bundle.get("resourceType") != "Bundle":
        errors.append("Missing or invalid resourceType (expected 'Bundle')")

    if bundle.get("type") not in ("document", "collection", "transaction", "batch"):
        errors.append(f"Invalid bundle type: {bundle.get('type')}")

    entries = bundle.get("entry", [])
    if not entries:
        errors.append("Bundle has no entries")

    resource_types_found = set()
    for i, entry in enumerate(entries):
        resource = entry.get("resource", {})
        rt = resource.get("resourceType", "")
        if not rt:
            errors.append(f"Entry {i} missing resourceType")
        resource_types_found.add(rt)

        if not entry.get("fullUrl"):
            errors.append(f"Entry {i} ({rt}) missing fullUrl")

    if "Patient" not in resource_types_found:
        errors.append("Bundle missing Patient resource")

    if "DiagnosticReport" not in resource_types_found:
        errors.append("Bundle missing DiagnosticReport resource")

    return errors
