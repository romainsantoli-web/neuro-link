# 🚀 LAUNCH.md — Neuro-Link v18 Launch Checklist

Stratégie de lancement gratuite pour maximiser la visibilité de Neuro-Link.

---

## 📋 Pré-lancement (J-7)

- [ ] **OG Image** : Ouvrir `public/og-image.html` dans Chrome, screenshot 1200×630px → sauver en `public/og-image.png`
- [ ] **Vérifier SEO** : Tester `landing.html` avec [Google Rich Results Test](https://search.google.com/test/rich-results)
- [ ] **Vérifier Open Graph** : Tester avec [opengraph.xyz](https://www.opengraph.xyz/) et [Twitter Card Validator](https://cards-dev.twitter.com/validator)
- [ ] **Google Search Console** : Soumettre sitemap.xml (`https://neuro-link.ai/sitemap.xml`)
- [ ] **GitHub Release** : Créer la release v18.0.0 avec le CHANGELOG.md
- [ ] **arXiv** : Soumettre le preprint `paper/ADFormerHybrid_preprint.tex`
- [ ] **README** : Vérifier le rendu sur GitHub (badges, tableau, architecture)

---

## 🎯 Jour J — Lancement

### 1. Product Hunt

- [ ] Soumettre sur [producthunt.com](https://www.producthunt.com)
- **Titre** : `Neuro-Link — Alzheimer Detection from EEG in 7 seconds`
- **Tagline** : `Open-source AI platform that detects Alzheimer's disease from EEG with 99.95% accuracy using a hybrid Transformer`
- **Description** :
  ```
  Neuro-Link is an open-source platform for early Alzheimer's disease detection.
  
  Upload an EEG file → Get a clinical report in 7 seconds.
  
  🧠 99.95% screening accuracy (AD vs Cognitively Normal)
  📊 97.79% severity staging confidence (Mild/Moderate/Severe)
  🔬 ADFormerHybrid: dual-branch Transformer + 267 EEG features
  📡 Works with $249 OpenBCI headsets
  🔒 Privacy-first: no cookies, no tracking, data never leaves your server
  
  Free for research. API plans for clinics ($50-$1000/month).
  ```
- **Topics** : `Artificial Intelligence`, `Health`, `Open Source`, `SaaS`, `Medical`
- **Thumbnail** : Utiliser `og-image.png`

### 2. Hacker News

- [ ] Soumettre comme **Show HN**
- **Titre** : `Show HN: Neuro-Link – Open-source Alzheimer's detection from EEG (99.95% accuracy)`
- **URL** : `https://github.com/romainsantoli-web/neuro-link`
- **Commentaire initial** :
  ```
  Hi HN, I built Neuro-Link to make Alzheimer's screening accessible.
  
  The core is ADFormerHybrid — a dual-branch Transformer that combines raw EEG 
  patches with 267 engineered features (spectral, entropy, graph connectivity).
  5 models vote via soft-voting for robustness.
  
  It works with $249 OpenBCI headsets and processes in 7 seconds on CPU.
  No GPU required.
  
  Stack: Python/FastAPI + React/TypeScript + PyTorch.
  Deployed on Oracle Cloud Always Free (ARM A1).
  
  Free for research. AGPL v3. Looking for feedback from neuroscientists
  and ML practitioners.
  ```
- **Timing** : Poster mardi ou mercredi, 14h-15h UTC

### 3. Reddit

- [ ] **r/MachineLearning** : `[P] Neuro-Link: Dual-branch Transformer for Alzheimer's EEG detection (99.95% accuracy, open-source)`
- [ ] **r/neuroscience** : Focus sur l'aspect clinique et le pipeline EEG
- [ ] **r/OpenBCI** : Focus sur la compatibilité hardware et le coût ($249)
- [ ] **r/selfhosted** : Focus sur le déploiement Oracle Cloud gratuit
- [ ] **r/artificial** : Vue d'ensemble de l'IA médicale

### 4. LinkedIn

- [ ] Post professionnel en français :
  ```
  🧠 Fier de lancer Neuro-Link v18 — une plateforme open-source de dépistage 
  précoce de la maladie d'Alzheimer par IA et EEG.
  
  ✅ 99.95% de précision au dépistage
  ✅ 97.79% de confiance au staging de sévérité
  ✅ Analyse complète en 7 secondes
  ✅ Compatible avec les casques EEG à 249$
  
  Architecture ADFormerHybrid : Transformer dual-branch à 4 couches combinant 
  des patches de signal brut avec 267 features EEG engineered.
  
  Gratuit pour la recherche. Code source sous AGPL v3.
  
  #Alzheimer #EEG #AI #DeepLearning #HealthTech #OpenSource #NeuralNetworks
  ```

### 5. Twitter / X

- [ ] Thread en anglais (5-7 tweets) :
  ```
  1/ 🧠 Launching Neuro-Link v18 — open-source Alzheimer's detection from EEG.
  99.95% screening accuracy. 7-second analysis. Works with $249 headsets.
  
  2/ The core is ADFormerHybrid: a dual-branch Transformer that combines raw 
  EEG patches with 267 engineered features (spectral, entropy, connectivity).
  
  3/ Pipeline: Upload EEG → Screening (AD vs CN) → Severity staging 
  (Mild/Moderate/Severe) → Clinical report with explainability.
  
  4/ 5 independent models vote via soft-voting. No GPU needed — runs on 
  CPU in 7 seconds. Deployed on Oracle Cloud Always Free.
  
  5/ Free for research. API plans for clinics.
  AGPL v3 open source.
  
  GitHub: github.com/romainsantoli-web/neuro-link
  ```

---

## 📡 Post-lancement (J+1 à J+30)

### Semaine 1
- [ ] Répondre à TOUS les commentaires (PH, HN, Reddit, LinkedIn)
- [ ] Écrire un article technique sur **dev.to** ou **Medium** : "How I Built an Alzheimer's Detection AI with 99.95% Accuracy"
- [ ] Cross-poster sur **Hashnode** et **Substack**
- [ ] Vérifier Google Analytics / `/analytics` endpoint pour les premiers metrics

### Semaine 2
- [ ] Soumettre à **Awesome lists** : awesome-machine-learning, awesome-healthcare, awesome-eeg
- [ ] Contacter 5-10 chercheurs en neurosciences (email personnalisé avec le preprint)
- [ ] Créer une démo vidéo (2-3 minutes) : upload EEG → résultat → rapport

### Semaine 3
- [ ] Soumettre à des newsletters : TLDR, The Batch (Andrew Ng), Import AI
- [ ] Contacter des podcasts tech/santé fr : Underscore_, NipTech, Tech Café
- [ ] Écrire un post LinkedIn sur les retours utilisateurs

### Semaine 4
- [ ] Bilan du mois : métriques, feedback, roadmap v19
- [ ] Publier les résultats dans le README (stars, forks, analyses effectuées)
- [ ] Planifier v19 features basées sur le feedback communautaire

---

## 📊 KPIs à suivre

| Métrique | Objectif J+30 | Outil |
|----------|---------------|-------|
| GitHub Stars | > 100 | GitHub |
| Page Views (landing) | > 5000 | `/analytics` endpoint |
| Analyses effectuées | > 50 | `/metrics` endpoint |
| Hacker News points | > 50 | HN |
| Product Hunt upvotes | > 100 | PH |
| Reddit karma total | > 200 | Reddit |
| LinkedIn impressions | > 10 000 | LinkedIn Analytics |

---

## 🆓 Outils gratuits utilisés

- **SEO** : Google Search Console, Rich Results Test
- **Social** : Open Graph debuggers, Twitter Card Validator
- **Analytics** : Endpoint `/analytics` maison (privacy-first)
- **CI/CD** : GitHub Actions (gratuit open-source)
- **Hébergement** : Oracle Cloud Always Free (4 ARM cores, 24GB RAM)
- **Email** : contact@neuro-link.ai
- **DNS** : Cloudflare Free (si applicable)

---

*Dernière mise à jour : Janvier 2025*
