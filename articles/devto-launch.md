---
title: "Neuro-Link — Open-Source Alzheimer Detection from EEG with 99.95% Accuracy"
published: false
description: "We built an open-source platform that detects Alzheimer's disease from standard EEG recordings using a dual-branch Transformer architecture. Here's how."
tags: machinelearning, opensource, healthcare, python
cover_image: https://neuro-link.ai/og-image.png
canonical_url: https://neuro-link.ai
---

## TL;DR

**Neuro-Link** is an open-source platform that detects Alzheimer's disease from standard EEG recordings with **99.95% accuracy** — in **7 seconds**, on **CPU only**. No MRI. No PET scan. No €3,000 bill.

🔗 [GitHub](https://github.com/romainsantoli-web/neuro-link) | 🌐 [Website](https://neuro-link.ai)

---

## The Problem

Alzheimer's disease affects **55 million people** worldwide. Current diagnostic methods require:

- **MRI/PET scans**: €800–3,000 per session
- **Specialized facilities**: Only available in major hospitals
- **Long wait times**: Weeks to months for results
- **Late detection**: Often diagnosed when damage is irreversible

Meanwhile, **EEG** (electroencephalography) is:
- ✅ Non-invasive
- ✅ Portable (headsets from €429)
- ✅ Fast (minutes to record)
- ✅ Affordable
- ❌ But historically hard to interpret for Alzheimer's detection

## Our Solution: ADFormerHybrid

We designed **ADFormerHybrid**, a dual-branch Transformer architecture that combines:

1. **Raw EEG patches** → Temporal Transformer branch
2. **267 engineered features** → Feature Transformer branch
   - Spectral: PSD across δ/θ/α/β/γ bands
   - Entropy: Sample, permutation, spectral entropy
   - Connectivity: Phase-Locking Value (PLV), coherence graphs

Both branches are fused and pass through an ensemble of **5 independently-trained models** with soft voting.

### Results

| Metric | Screening (AD vs CN) | Staging (Severity) |
|--------|----------------------|-------------------|
| Accuracy | **99.95%** | **97.79%** |
| Pipeline time | 7 seconds (CPU) | Included |
| GPU required | No | No |

## Architecture

```
EEG File (.edf/.set/.bdf/...)
    │
    ├─ Preprocessing (MNE-Python)
    │   ├─ Bandpass 0.5-45 Hz
    │   ├─ ICA artifact removal
    │   └─ 19-channel standard montage
    │
    ├─ Feature Extraction (267 features)
    │   ├─ Spectral (PSD, band powers)
    │   ├─ Entropy (sample, permutation, spectral)
    │   └─ Connectivity (PLV, coherence)
    │
    └─ ADFormerHybrid Ensemble (×5)
        ├─ Branch A: Raw EEG Patches → Transformer
        ├─ Branch B: 267 Features → Transformer
        └─ Soft Voting → Result
```

## Tech Stack

- **Backend**: Python 3.11, FastAPI, PyTorch, MNE-Python
- **Frontend**: React 18, TypeScript, Vite 6, Recharts
- **Deployment**: Oracle Cloud Always Free (ARM A1, 4 OCPUs, 24GB RAM)
- **Tests**: 118 total (48 vitest + 70 pytest), all passing
- **License**: AGPL v3 (open-source) + Commercial option

## Key Features

### 🧠 Clinical-Grade Output
Every analysis produces a full PDF report with:
- Screening result (AD-positive / Cognitively Normal)
- Severity staging (Mild / Moderate / Severe) if AD-positive
- Top contributing features with interpretability
- AI-generated clinical narrative (via Gemini Pro)
- FHIR R4 export for medical record integration

### 🔒 Privacy-First
- Zero cookies, zero third-party tracking
- EEG data never leaves your server
- Self-hosted deployment
- Open-source and auditable

### 📡 7 EEG Formats Supported
`.set` (EEGLAB), `.edf`, `.bdf` (BioSemi), `.vhdr` (BrainVision), `.fif` (MNE), `.csv`, `.txt` (OpenBCI)

### 💰 Free Tier
5 analyses/month, all formats, full reports — forever free for researchers.

## Quick Start

```bash
# Clone
git clone https://github.com/romainsantoli-web/neuro-link.git
cd neuro-link

# Backend
cd backend
pip install -r requirements.txt
python -m uvicorn app:app --host 0.0.0.0 --port 8000

# Frontend (new terminal)
npm install && npm run dev
```

Open `http://localhost:3000` and upload an EEG file.

## What's Next (Phase 3)

- [ ] Real-time EEG streaming (WebSocket)
- [ ] Longitudinal patient tracking
- [ ] CE/FDA certification pathway
- [ ] Multi-language clinical reports
- [ ] Mobile companion app

## Try It

- 🔗 **GitHub**: [romainsantoli-web/neuro-link](https://github.com/romainsantoli-web/neuro-link)
- 🌐 **Website**: [neuro-link.ai](https://neuro-link.ai)
- 📄 **Paper**: Available in the repo (`paper/` directory)

We'd love your feedback — issues, PRs, and stars are all welcome.

---

*Built by [Romain Kocupyr](https://github.com/romainsantoli-web). If you're working on neuroscience, EEG, or Alzheimer's research, let's connect.*

## Citation

```bibtex
@software{kocupyr2025neurolink,
  title   = {Neuro-Link: Open-Source Alzheimer Detection from EEG},
  author  = {Kocupyr, Romain},
  year    = {2025},
  url     = {https://github.com/romainsantoli-web/neuro-link},
  version = {18.0.0}
}
```
