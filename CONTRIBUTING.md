# Contribuer à Neuro-Link

Merci de votre intérêt pour Neuro-Link ! Ce guide vous aidera à contribuer efficacement.

## Prérequis

- Python 3.11+
- Node.js 20+
- Git

## Mise en place de l'environnement

```bash
# Cloner le repo
git clone https://github.com/romainkocupyr/neuro-link.git
cd neuro-link

# Backend
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements.txt
pip install -r requirements-ml.txt
pip install pytest ruff

# Frontend
npm ci
```

## Structure du projet

```
├── App.tsx / components/     # Frontend React
├── backend/app.py            # API FastAPI
├── alz-finis/                # Pipeline ML
│   ├── eeg_io.py             # Chargement EEG multi-format
│   ├── adformer_hybrid_voting_full.py  # Modèle ADFormerHybrid
│   ├── run_pipeline.py       # Orchestrateur screening → staging
│   ├── Dépistage/            # Scripts + modèles dépistage
│   └── ad_id_99_c_scaler/    # Scripts + modèles staging
├── deploy/                   # Nginx + systemd configs
├── tests/                    # Tests pytest + vitest
└── public/                   # Landing page
```

## Workflow de contribution

1. **Fork** le repo et créez une branche depuis `main`
2. Nommez votre branche : `feature/description`, `fix/description`, ou `docs/description`
3. Faites vos modifications
4. Lancez les vérifications :
   ```bash
   # Lint Python
   ruff check backend/ alz-finis/ --select E,F,W --ignore E501,F401,E402

   # Syntax check
   python3 -m py_compile backend/app.py alz-finis/run_pipeline.py

   # Tests
   pytest tests/ -v

   # Frontend
   npx tsc --noEmit
   npm run build
   ```
5. Commitez avec un message clair (convention Conventional Commits) :
   ```
   feat: add FHIR export endpoint
   fix: handle empty EEG segments in eeg_io
   docs: update deployment guide
   ```
6. Ouvrez une **Pull Request** vers `main`

## Conventions de code

### Python
- Style : PEP 8 (vérifié par Ruff)
- Type hints obligatoires pour les fonctions publiques
- Docstrings en français pour les modules médicaux
- `f-strings` pour le formatage

### TypeScript / React
- Composants fonctionnels avec `React.FC<Props>`
- Pas de `any` — utiliser les types de `types.ts`
- Tailwind CSS pour le styling

## Domaines de contribution

### Haute priorité
- Tests unitaires et d'intégration (voir `tests/`)
- Validation sur de nouveaux jeux de données EEG
- Support de formats EEG additionnels
- Documentation et traductions

### Contributions avancées
- Optimisation du modèle ADFormerHybrid
- Export PDF des rapports cliniques
- Intégration HL7/FHIR
- Applications mobiles

## Données sensibles

- **JAMAIS** de données patient dans les PRs ou issues
- Les poids de modèles (`.pth`) ne sont pas versionnés — utilisez Git LFS si nécessaire
- Les fichiers `.env` sont dans le `.gitignore`

## Licence

En contribuant, vous acceptez que vos contributions soient soumises à la licence AGPL v3.0 du projet (voir [LICENSE](LICENSE)).

## Questions ?

Ouvrez une issue sur GitHub ou contactez : **romain.kocupyr@neuro-link.ai**
