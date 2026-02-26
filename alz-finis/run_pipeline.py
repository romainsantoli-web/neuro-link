#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import argparse
import json
import os
import re
import subprocess
import sys
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional, Tuple


def _extract_confidence(report_text: str) -> float:
    match = re.search(r"Confiance\s*:\s*([0-9]+(?:[\.,][0-9]+)?)%", report_text, flags=re.IGNORECASE)
    if not match:
        return 0.0
    value = match.group(1).replace(',', '.')
    try:
        return float(value) / 100.0
    except ValueError:
        return 0.0


def _extract_prediction(report_text: str) -> str:
    match = re.search(r"Prédiction\s*IA\s*:\s*([^\n\r]+)", report_text, flags=re.IGNORECASE)
    if not match:
        return ""
    return match.group(1).strip()


def _read_report(report_path: Path) -> str:
    if not report_path.exists():
        return ""
    return report_path.read_text(encoding='utf-8', errors='ignore')


def _build_command(
    python_exec: str,
    script_path: Path,
    file_path: str,
    name: str,
    output_prefix: str,
    mode: str,
    openbci_fs: float,
    model_path: Optional[str],
    scaler_path: Optional[str],
    model_paths: Optional[list] = None,
) -> list:
    command = [
        python_exec,
        str(script_path),
        '--file', file_path,
        '--name', name,
        '--output', output_prefix,
        '--mode', mode,
        '--openbci_fs', str(openbci_fs),
    ]

    if model_paths and len(model_paths) > 0:
        command.extend(['--models'] + [str(p) for p in model_paths])
    elif model_path:
        command.extend(['--model', model_path])
    if scaler_path:
        command.extend(['--scaler', scaler_path])

    return command


def _run_step(command: list, cwd: Path) -> Tuple[int, str, str]:
    process = subprocess.run(command, capture_output=True, text=True, cwd=str(cwd))
    return process.returncode, process.stdout, process.stderr


def _normalize_status(screening_prediction: str) -> str:
    pred = screening_prediction.upper()
    if 'AD' in pred and 'CN' not in pred:
        return 'ALZHEIMER'
    if 'CN' in pred or 'NON' in pred:
        return 'NON-ALZHEIMER'
    return 'INCONCLUSIVE'


def _normalize_stage(staging_prediction: str) -> str:
    pred = staging_prediction.lower()
    if 'léger' in pred or 'leger' in pred or 'début' in pred or 'debut' in pred:
        return 'Stade 1 (Début)'
    if 'modéré' in pred or 'modere' in pred:
        return 'Stade 2 (Modéré)'
    if 'sévère' in pred or 'severe' in pred or 'avancé' in pred or 'avance' in pred:
        return 'Stade 3 (Avancé)'
    return 'Inconnu'


def _default_paths(base_dir: Path) -> Dict[str, Any]:
    return {
        'screening_script': base_dir / 'Dépistage' / 'ad_depistage_alz_scaler' / 'depistage_patient_from_set.py',
        'staging_script': base_dir / 'ad_id_99_c_scaler' / 'predict_patient_from_set.py',
        'screening_model': base_dir / 'Dépistage' / 'adformer_depis_scaler_v1.pth',
        'screening_scaler': base_dir / 'Dépistage' / 'adformer_depis_scaler_v1_scaler.pkl',
        'staging_model': base_dir / 'ad_id_99_c_scaler' / 'adformer_id_c_scaler_v1.pth',
        'staging_scaler': base_dir / 'ad_id_99_c_scaler' / 'adformer_id_c_scaler_v1_scaler.pkl',
        'screening_models': [
            base_dir / 'Dépistage' / f'adformer_depis_scaler_v{i}.pth' for i in range(1, 6)
        ],
        'staging_models': [
            base_dir / 'ad_id_99_c_scaler' / f'adformer_id_c_scaler_v{i}.pth' for i in range(1, 6)
        ],
    }


def main() -> int:
    base_dir = Path(__file__).resolve().parent
    defaults = _default_paths(base_dir)

    parser = argparse.ArgumentParser(description='Pipeline EEG: dépistage puis staging si positif AD')
    parser.add_argument('--file', required=True, help='Chemin du fichier EEG (MNE ou OpenBCI csv/txt)')
    parser.add_argument('--name', default=f'patient_{uuid.uuid4().hex[:8]}', help='Identifiant patient')
    parser.add_argument('--output_dir', default=str(base_dir / 'results_pipeline'), help='Dossier de sortie pipeline')
    parser.add_argument('--mode', default='soft', choices=['soft', 'hard'], help='Mode de prédiction des scripts')
    parser.add_argument('--openbci_fs', type=float, default=250.0, help='Fréquence source OpenBCI si timestamp absent')
    parser.add_argument('--python_exec', default=sys.executable, help='Interpréteur Python pour lancer les scripts')

    parser.add_argument('--screening_script', default=str(defaults['screening_script']), help='Script de dépistage')
    parser.add_argument('--staging_script', default=str(defaults['staging_script']), help='Script de staging')

    parser.add_argument('--screening_model', default=str(defaults['screening_model']), help='Chemin modèle dépistage')
    parser.add_argument('--screening_scaler', default=str(defaults['screening_scaler']), help='Chemin scaler dépistage')
    parser.add_argument('--staging_model', default=str(defaults['staging_model']), help='Chemin modèle staging')
    parser.add_argument('--staging_scaler', default=str(defaults['staging_scaler']), help='Chemin scaler staging')
    parser.add_argument('--ensemble', action='store_true', default=True, help='Activer ensemble voting avec 5 modèles (par défaut: on)')
    parser.add_argument('--no-ensemble', dest='ensemble', action='store_false', help='Désactiver ensemble voting (1 seul modèle)')

    args = parser.parse_args()

    input_file = Path(args.file)
    if not input_file.exists():
        print(json.dumps({'error': f'Fichier introuvable: {input_file}'}), file=sys.stderr)
        return 2

    screening_script = Path(args.screening_script)
    staging_script = Path(args.staging_script)
    if not screening_script.exists() or not staging_script.exists():
        print(json.dumps({'error': 'Scripts pipeline introuvables'}), file=sys.stderr)
        return 2

    run_id = datetime.now().strftime('%Y%m%d_%H%M%S')
    run_dir = Path(args.output_dir) / f'{args.name}_{run_id}'
    run_dir.mkdir(parents=True, exist_ok=True)

    # Déterminer les modèles à utiliser (ensemble ou single)
    screening_models = [str(p) for p in defaults['screening_models'] if p.exists()] if args.ensemble else []
    staging_models = [str(p) for p in defaults['staging_models'] if p.exists()] if args.ensemble else []

    screening_prefix = str(run_dir / 'screening_')
    screening_cmd = _build_command(
        python_exec=args.python_exec,
        script_path=screening_script,
        file_path=str(input_file),
        name=args.name,
        output_prefix=screening_prefix,
        mode=args.mode,
        openbci_fs=args.openbci_fs,
        model_path=args.screening_model,
        scaler_path=args.screening_scaler,
        model_paths=screening_models,
    )

    screening_code, screening_stdout, screening_stderr = _run_step(screening_cmd, cwd=screening_script.parent)
    screening_dir = Path(f'{screening_prefix}{args.name}')
    screening_report = screening_dir / f'rapport_{args.name}_{args.mode}.txt'
    screening_text = _read_report(screening_report)

    screening_prediction = _extract_prediction(screening_text)
    screening_confidence = _extract_confidence(screening_text)
    status = _normalize_status(screening_prediction)

    result = {
        'status': status,
        'stage': 'N/A',
        'confidence': screening_confidence,
        'features': {},
        'report': screening_text,
        'pipeline': {
            'run_id': run_id,
            'screening': {
                'command': screening_cmd,
                'exit_code': screening_code,
                'stdout': screening_stdout,
                'stderr': screening_stderr,
                'report_path': str(screening_report),
                'prediction': screening_prediction,
            },
            'staging': None,
        },
        'created_at': datetime.now().isoformat(),
    }

    if screening_code != 0:
        result['status'] = 'INCONCLUSIVE'
        result['stage'] = 'Inconnu'
        result['report'] = screening_text or screening_stderr
        result_path = run_dir / 'result.json'
        result_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
        print(json.dumps(result, ensure_ascii=False))
        return 1

    if status == 'ALZHEIMER':
        staging_prefix = str(run_dir / 'staging_')
        staging_cmd = _build_command(
            python_exec=args.python_exec,
            script_path=staging_script,
            file_path=str(input_file),
            name=args.name,
            output_prefix=staging_prefix,
            mode=args.mode,
            openbci_fs=args.openbci_fs,
            model_path=args.staging_model,
            scaler_path=args.staging_scaler,
            model_paths=staging_models,
        )

        staging_code, staging_stdout, staging_stderr = _run_step(staging_cmd, cwd=staging_script.parent)
        staging_dir = Path(f'{staging_prefix}{args.name}')
        staging_report = staging_dir / f'rapport_{args.name}_{args.mode}.txt'
        staging_text = _read_report(staging_report)
        staging_prediction = _extract_prediction(staging_text)
        staging_confidence = _extract_confidence(staging_text)

        result['stage'] = _normalize_stage(staging_prediction)
        result['confidence'] = staging_confidence if staging_confidence > 0 else screening_confidence
        result['report'] = staging_text or screening_text
        result['pipeline']['staging'] = {
            'command': staging_cmd,
            'exit_code': staging_code,
            'stdout': staging_stdout,
            'stderr': staging_stderr,
            'report_path': str(staging_report),
            'prediction': staging_prediction,
        }

        if staging_code != 0:
            result['status'] = 'INCONCLUSIVE'
            result['stage'] = 'Inconnu'

    result_path = run_dir / 'result.json'
    result_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
