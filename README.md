<div align="center">

# 🧠 NEURO-LINK v18

**Dépistage précoce de la maladie d'Alzheimer par IA hybride Transformer & EEG**

*Early Alzheimer's Disease detection from EEG using a hybrid Transformer AI*

[![License: AGPL v3](https://img.shields.io/badge/License-AGPL%20v3-blue.svg)](https://www.gnu.org/licenses/agpl-3.0)
[![Python 3.11+](https://img.shields.io/badge/Python-3.11+-3776AB.svg?logo=python&logoColor=white)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-009688.svg?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![React 18](https://img.shields.io/badge/React-18-61DAFB.svg?logo=react&logoColor=white)](https://react.dev)
[![TypeScript](https://img.shields.io/badge/TypeScript-5.8-3178C6.svg?logo=typescript&logoColor=white)](https://typescriptlang.org)
[![Oracle Cloud](https://img.shields.io/badge/Oracle%20Cloud-Always%20Free-F80000.svg?logo=oracle&logoColor=white)](https://cloud.oracle.com)

[**Site Web**](https://neuro-link.ai) · [**Documentation**](#-quick-start) · [**Paper**](#-paper--citation) · [**Contact**](mailto:romain.kocupyr@neuro-link.ai)

---

<table>
<tr>
<td align="center"><strong>99.95%</strong><br/><sub>Précision dépistage</sub></td>
<td align="center"><strong>97.79%</strong><br/><sub>Confiance staging</sub></td>
<td align="center"><strong>7s</strong><br/><sub>Temps d'analyse</sub></td>
<td align="center"><strong>267</strong><br/><sub>Features EEG</sub></td>
<td align="center"><strong>5×</strong><br/><sub>Modèles ensemble</sub></td>
</tr>
</table>

</div>

---

## 🎯 Why Neuro-Link?

> La maladie d'Alzheimer touche **55 millions de personnes** dans le monde. Un diagnostic précoce peut ralentir la progression de 40%. Neuro-Link démocratise le dépistage avec un simple EEG, un casque abordable ($249), et l'IA.

| Problème | Solution Neuro-Link |
|---|---|
| IRM coûteuse (500-3000€) | EEG accessible ($249 avec OpenBCI) |
| Délai diagnostic 2-5 ans | Résultat en 7 secondes |
| Interprétation subjective | IA reproductible à 99.95% |
| Accès limité aux spécialistes | Plateforme web accessible partout |

---

## 🏗️ Architecture

```
┌──────────────────────────────────────────────────────────────┐
│                    NEURO-LINK v18                             │
├─────────────────────┬────────────────────────────────────────┤
│   Frontend (React)  │          Backend (FastAPI)             │
│                     │                                        │
│  ┌──────────────┐   │   ┌─────────────┐  ┌──────────────┐   │
│  │  StatusHUD   │   │   │   /analyze  │  │  Monitoring  │   │
│  │  ConsoleBox  │   │   │   /health   │  │  /metrics    │   │
│  │  NarratorBox │   │   │   /memory/* │  │              │   │
│  │  ResultsDash │   │   └──────┬──────┘  └──────────────┘   │
│  └──────────────┘   │          │                             │
│                     │   ┌──────▼──────────────────────┐      │
│                     │   │   ADFormerHybrid Pipeline   │      │
│                     │   │                             │      │
│                     │   │  ┌─────────┐ ┌──────────┐  │      │
│                     │   │  │Screening│→│ Staging  │  │      │
│                     │   │  │ AD/CN   │ │ L/M/S    │  │      │
│                     │   │  └─────────┘ └──────────┘  │      │
│                     │   │                             │      │
│                     │   │  267 Features × 5 Models   │      │
│                     │   │  Soft-Voting Ensemble       │      │
│                     │   └─────────────────────────────┘      │
├─────────────────────┴────────────────────────────────────────┤
│  Reports: PDF + FHIR R4 + Gemini AI Narrative               │
│  Security: Rate Limit · Bearer Auth · TLS · Sandboxing       │
│  Deploy: Oracle Cloud ARM A1 · Nginx · systemd · GitHub CI  │
└──────────────────────────────────────────────────────────────┘
```

### ADFormerHybrid — Le modèle

Architecture **dual-branch Transformer** à 4 couches :

- **Branche 1 — Raw Patch Encoder** : Patches de signal EEG brut → Transformer attention
- **Branche 2 — Feature Encoder** : 267 features engineered (spectral, entropy, graph connectivity)
- **Fusion** : Concaténation + MLP classifier
- **Ensemble** : Soft-voting sur 5 checkpoints indépendants → confiance calibrée

---

## 🚀 Quick Start

### Prérequis

- **Node.js** ≥ 18
- **Python** ≥ 3.11
- **PyTorch** ≥ 2.0
- Clé API Gemini (optionnelle, pour les rapports IA)

### Installation

```bash
# 1. Cloner le dépôt
git clone https://github.com/romainsantoli-web/neuro-link.git
cd neuro-link

# 2. Installer le frontend
npm install

# 3. Installer le backend
python3 -m pip install -r backend/requirements.txt

# 4. Configurer les variables d'environnement
cp backend/.env.prod.example .env.local
# Éditer .env.local avec votre clé Gemini et paramètres

# 5. Lancer le tout
npm run dev          # Frontend (Vite)
npm run api          # Backend (FastAPI)
```

### Analyse rapide (CLI)

```bash
python3 alz-finis/run_pipeline.py --file <path_to_eeg.set>

# Avec OpenBCI
python3 alz-finis/run_pipeline.py --file <openbci.csv> --openbci_fs 250
```

---

## 📡 API Endpoints

| Méthode | Route | Description |
|---------|-------|-------------|
| `GET` | `/health` | Health check |
| `POST` | `/analyze` | Analyse EEG complète (screening + staging) |
| `GET` | `/metrics` | Métriques Prometheus-compatible |
| `GET` | `/memory/health` | État du pipeline mémoire |
| `POST` | `/memory/context` | Contexte de session |
| `POST` | `/memory/ingest` | Stockage des résultats |

### Exemple d'analyse

```bash
curl -X POST https://neuro-link.ai/api/analyze \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@patient_eeg.set"
```

<details>
<summary>📋 Réponse JSON</summary>

```json
{
  "screening": {
    "prediction": "AD",
    "confidence": 0.9995,
    "votes": {"AD": 5, "CN": 0}
  },
  "staging": {
    "prediction": "Moderate",
    "confidence": 0.9779,
    "probabilities": {"Mild": 0.012, "Moderate": 0.978, "Severe": 0.010}
  },
  "top_features": ["..."],
  "processing_time_seconds": 6.8
}
```

</details>

---

## 📊 Formats EEG supportés

| Format | Extension | Source |
|--------|-----------|--------|
| EEGLAB | `.set` | MATLAB/EEGLAB |
| European Data Format | `.edf` | Standard clinique |
| BioSemi | `.bdf` | BioSemi hardware |
| BrainVision | `.vhdr` | Brain Products |
| MNE-Python | `.fif` | MNE ecosystem |
| OpenBCI | `.csv`, `.txt` | OpenBCI ($249) |

---

## 💰 Tarifs

| Plan | Prix | Analyses | Utilisateurs | Fonctionnalités |
|------|------|----------|--------------|-----------------|
| **Recherche** | Gratuit | Illimitées | 1 | Rapport clinique, watermark |
| **Starter** | 50€/mois | 100/mois | 1 | API REST, rapport PDF |
| **Clinique** | 250€/mois | 500/mois | 5 | PDF personnalisé, support prioritaire |
| **Institution** | 1000€/mois | Illimitées | Multi-sites | SLA 99.9%, intégration DPI, 24/7 |

---

## 🔒 Sécurité

- **Rate limiting** dynamique avec blocage IP temporaire
- **Détection d'injection** (SQL, XSS, path traversal)
- **Authentification Bearer** (optionnelle, obligatoire en mode strict)
- **TLS** end-to-end avec Nginx
- **Headers de sécurité** (nosniff, frame deny, no-store)
- **Sandboxing systemd** en production
- **Pas de cookies de tracking** — Respect total de la vie privée

---

## 🏥 Conformité & Exports

- **HL7 FHIR R4** — Export standardisé pour intégration DPI (Dossier Patient Informatisé)
- **Rapport PDF** — Rapport clinique professionnel avec en-tête médical
- **Rapport IA** — Narration clinique générée par Gemini Pro
- **Licence duale** — AGPL v3 (open source) + Commercial

---

## 🚢 Déploiement Production

<details>
<summary>Oracle Cloud Always Free (ARM A1)</summary>

```bash
# 4 OCPUs ARM, 24 GB RAM — gratuit à vie
# Voir deploy/nginx/neuro-link.conf et deploy/systemd/neuro-link-api.service
```

</details>

<details>
<summary>Nginx + TLS</summary>

```bash
sudo cp deploy/nginx/neuro-link.conf /etc/nginx/sites-available/
sudo ln -s /etc/nginx/sites-available/neuro-link.conf /etc/nginx/sites-enabled/
sudo nginx -t && sudo systemctl reload nginx
```

</details>

<details>
<summary>systemd Auto-Start</summary>

```bash
sudo cp deploy/systemd/neuro-link-api.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now neuro-link-api
```

</details>

---

## 📄 Paper & Citation

Architecture décrite dans le preprint **ADFormerHybrid** :

> **ADFormerHybrid: A Dual-Branch Transformer for Alzheimer's Disease Detection from EEG**
> *Romain Kocupyr, 2025*

```bibtex
@article{kocupyr2025adformerhybrid,
  title     = {ADFormerHybrid: A Dual-Branch Transformer for Alzheimer's Disease Detection from EEG},
  author    = {Kocupyr, Romain},
  year      = {2025},
  note      = {Preprint — Neuro-Link v18},
  url       = {https://github.com/romainsantoli-web/neuro-link}
}
```

---

## 🤝 Contribuer

Les contributions sont les bienvenues ! Consultez [CONTRIBUTING.md](CONTRIBUTING.md) et [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md).

```bash
# Fork + clone
git checkout -b feature/my-feature
# ... développer ...
npm test              # 48 tests frontend (vitest)
pytest backend/       # 70 tests backend
git commit -m "feat: description"
git push origin feature/my-feature
```

---

## 📜 Licence

**Dual License** — [AGPL v3](LICENSE) pour usage open-source / [Commercial](mailto:romain.kocupyr@neuro-link.ai) pour usage clinique.

---

<div align="center">

**Neuro-Link v18** — *Créé par [Romain Kocupyr](mailto:romain.kocupyr@neuro-link.ai)*

⚠️ *Outil d'aide à la recherche. Ne constitue pas un diagnostic médical. Les résultats doivent être interprétés par un professionnel de santé qualifié. Dispositif non certifié CE/FDA.*

</div>