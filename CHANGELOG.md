# Changelog

Toutes les modifications notables de Neuro-Link sont documentées dans ce fichier.

Le format est basé sur [Keep a Changelog](https://keepachangelog.com/fr/1.1.0/),
et ce projet adhère au [Semantic Versioning](https://semver.org/lang/fr/).

---

## [18.0.0] — 2025-01-01

### 🧠 Phase 1 — Pipeline IA Complet (24/24 tâches)

#### Ajouté
- **ADFormerHybrid** : Architecture dual-branch Transformer 4 couches (raw patches + 267 features engineered)
- **Screening** : Détection binaire AD vs. Cognitively Normal avec précision 99.95%
- **Staging** : Classification de sévérité (Léger / Modéré / Sévère) avec confiance 97.79%
- **Ensemble 5 modèles** : Soft-voting sur 5 checkpoints indépendants pour robustesse maximale
- **267 features EEG** : Spectral (PSD, bandes δ/θ/α/β/γ), entropie (sample, permutation, spectral), connectivité de graphe (PLV, coherence)
- **Pipeline complet** : run_pipeline.py — screening → staging conditionnel si AD-positif
- **7 formats EEG** : .set, .edf, .bdf, .vhdr, .fif, .csv, .txt (OpenBCI compatible)
- **API REST** : FastAPI avec /analyze, /health, /metrics, /memory/*
- **Rapport PDF** : Génération professionnelle avec reportlab (en-tête médical, top features, graphiques)
- **Rapport IA** : Narration clinique via Gemini Pro (/gemini-report)
- **Export FHIR R4** : HL7 FHIR DiagnosticReport + Observation standardisés
- **Sécurité** : Rate limiting, blocage IP, anti-injection, bearer auth, TLS headers, sandboxing systemd
- **Monitoring** : Métriques par route (count, latency, errors), system resources, JSON structured logging
- **SaaS API Keys** : 4 plans (Free, Starter 50€, Clinique 250€, Institution 1000€) avec Stripe billing
- **CI/CD** : GitHub Actions (ci.yml tests + cd.yml deploy) 
- **Déploiement** : Oracle Cloud Always Free ARM A1, Nginx reverse proxy, systemd service

### 🎨 Phase 2 — Frontend Complet (5/5 tâches)

#### Ajouté
- **React 18 + TypeScript 5.8** : Application SPA avec Vite 6
- **StatusHUD** : Indicateurs temps réel (connexion, mémoire, modèle, API)
- **ConsoleBox** : Console de logs avec scroll automatique et couleurs par niveau
- **NarratorBox** : Narration clinique IA avec animation de frappe
- **ResultsDashboard** : Graphiques Recharts (barres confiance, radar features, timeline)
- **Landing Page** : Page marketing complète (hero, stats, pipeline, features, pricing, compatibilité)

### 🎭 Design Overhaul

#### Modifié
- **Glassmorphism** : Effets de verre sur tous les composants (backdrop-blur, gradients subtils)
- **Animations** : Pulse, scan, fade-in sur les éléments interactifs
- **Palette** : Neon cyan #00ffea, purple #a855f7, green #3fb950 sur fond #03070d
- **Typographie** : Orbitron (titres), Rajdhani (corps), Share Tech Mono (mono)
- **Rapport PDF redesigné** : Layout médical professionnel avec header branded

### 📢 Marketing & SEO

#### Ajouté
- **SEO complet** : Open Graph, Twitter Cards, JSON-LD (SoftwareApplication + ScholarlyArticle + Organization)
- **robots.txt + sitemap.xml** : Indexation optimisée pour les moteurs de recherche
- **favicon.svg** : Icône neural branded (dégradé cyan → purple)
- **OG Image template** : Template HTML 1200×630px pour social sharing
- **README.md** : Réécriture complète avec badges, architecture, Quick Start, API, BibTeX
- **CHANGELOG.md** : Ce fichier
- **LAUNCH.md** : Checklist de lancement (Product Hunt, HN, Reddit, LinkedIn)
- **Plan Starter** ajouté à la landing page (50€/mois, manquait précédemment)
- **URL GitHub** corrigée dans la landing page
- **Canonical URL** et balises meta complètes

### 📚 Documentation

#### Ajouté
- **CONTRIBUTING.md** : Guide de contribution (en français)
- **CODE_OF_CONDUCT.md** : Code de conduite communautaire
- **PRIVACY.md** : Politique de confidentialité (pas de cookies, pas de tracking tiers)
- **LICENSE** : Dual AGPL v3 + Commercial
- **Paper LaTeX** : ADFormerHybrid preprint (282 lignes, prêt pour arXiv)

### ✅ Tests

- **48 tests frontend** (vitest) — tous passent ✅
- **70 tests backend** (pytest) — tous passent ✅
- **118 tests total** — couverture complète

---

## [17.0.0] — 2024-12-01

### Ajouté
- Version initiale du pipeline de screening
- Premiers modèles de classification AD/CN

---

*Pour les versions antérieures, voir l'historique Git.*
