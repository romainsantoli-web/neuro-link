# Déploiement Neuro-Link v18 — VPS Gratuit (Oracle Cloud)

## Pourquoi Oracle Cloud Always Free ?

| Fournisseur        | CPU         | RAM     | Stockage | Durée        | ML compatible |
|-------------------|-------------|---------|----------|--------------|---------------|
| **Oracle Cloud**  | **4 ARM**   | **24 GB** | **200 GB** | **∞ gratuit** | ✅ PyTorch CPU |
| Google Cloud      | 0.25 vCPU   | 1 GB    | 30 GB    | ∞ gratuit    | ❌ trop petit  |
| AWS Free Tier     | 1 vCPU      | 1 GB    | 30 GB    | 12 mois      | ❌ trop petit  |
| Azure             | 1 vCPU      | 1 GB    | 64 GB    | 12 mois      | ❌ trop petit  |

Oracle Cloud Always Free offre une instance **ARM Ampere A1** avec **4 OCPUs + 24 GB RAM** — largement suffisant pour PyTorch en inférence CPU + FastAPI + Nginx.

---

## 1. Créer le compte Oracle Cloud

1. Aller sur **[cloud.oracle.com/free](https://cloud.oracle.com/free)**
2. Créer un compte (carte bancaire requise mais **jamais débitée** pour le tier Always Free)
3. Choisir la région la plus proche (ex: `eu-paris-1` ou `eu-marseille-1`)

## 2. Créer l'instance VM

1. **Compute → Instances → Create Instance**
2. Configuration :
   - **Image** : Ubuntu 22.04 (Canonical)
   - **Shape** : VM.Standard.A1.Flex (ARM Ampere)
   - **OCPUs** : 4
   - **RAM** : 24 GB
   - **Boot volume** : 100 GB (extensible à 200 GB)
3. **Réseau** :
   - VCN par défaut, sous-réseau public
   - **Assign public IPv4** : oui
4. **SSH Key** : Uploader votre clé publique (`~/.ssh/id_ed25519.pub`)
5. **Créer** → attendre ~2 min le provisionnement

## 3. Configurer le réseau Oracle

> ⚠️ Oracle Cloud a un firewall réseau (Security Lists) EN PLUS du firewall OS.

1. **Networking → VCN → Security Lists → Default**
2. **Add Ingress Rules** :

| Port | Protocole | Source    | Description  |
|------|-----------|-----------|-------------|
| 80   | TCP       | 0.0.0.0/0 | HTTP        |
| 443  | TCP       | 0.0.0.0/0 | HTTPS       |
| 22   | TCP       | 0.0.0.0/0 | SSH (déjà)  |

## 4. Se connecter au VPS

```bash
ssh ubuntu@<IP_PUBLIQUE>
```

## 5. Déployer automatiquement

### Option A — Déploiement en une seule commande

```bash
# Cloner le repo et lancer le setup
git clone https://github.com/Romainmusic/neuro-link-v18.git /opt/neuro-link-v18
cd /opt/neuro-link-v18
sudo DOMAIN=neuro-link.example.com ./deploy/vps-setup.sh
```

### Option B — Sans domaine (accès par IP)

```bash
git clone https://github.com/Romainmusic/neuro-link-v18.git /opt/neuro-link-v18
cd /opt/neuro-link-v18
sudo ./deploy/vps-setup.sh
```

Le script installe automatiquement :
- Python 3.11 + venv + PyTorch (CPU) + toutes les dépendances ML
- Node.js 20 + build du frontend React
- Nginx (reverse proxy + fichiers statiques)
- Certificat TLS Let's Encrypt (si domaine fourni)
- Service systemd avec sandboxing
- Firewall UFW
- Token API auto-généré

## 6. Vérification post-déploiement

```bash
# Status du service
sudo systemctl status neuro-link-api

# Logs en temps réel
sudo journalctl -u neuro-link-api -f

# Health check
curl http://localhost:8000/health

# Test depuis l'extérieur
curl http://<IP_PUBLIQUE>/health
```

## 7. Ajouter un domaine (optionnel)

1. Acheter un domaine (ex: OVH, Namecheap, Cloudflare)
2. Ajouter un **enregistrement DNS A** pointant vers l'IP du VPS
3. Relancer le setup avec le domaine :

```bash
sudo DOMAIN=neuro-link.fr ./deploy/vps-setup.sh
```

## 8. Mise à jour du code

```bash
cd /opt/neuro-link-v18
git pull origin main
source .venv/bin/activate
pip install -r backend/requirements.txt -r requirements-ml.txt -q
npm ci --ignore-scripts && npm run build
cp -r dist/* /var/www/neuro-link-v18/
sudo systemctl restart neuro-link-api
```

Ou avec le CD automatique (GitHub Actions) : push sur `main` → déploiement auto.

## 9. Monitoring

```bash
# Métriques API (requiert le token)
TOKEN=$(grep SECURITY_BEARER_TOKEN /etc/neuro-link/backend.env | cut -d= -f2)
curl -H "Authorization: Bearer $TOKEN" http://localhost:8000/metrics | jq .

# Ressources système
htop

# Espace disque
df -h /
```

## 10. Coûts

| Composant                    | Coût        |
|------------------------------|-------------|
| VPS Oracle Cloud Always Free | **0 €/mois** |
| Domaine .fr (OVH)           | ~7 €/an     |
| TLS (Let's Encrypt)         | **0 €**     |
| **Total**                   | **~0.58 €/mois** |

---

## Architecture de déploiement

```
Internet
   │
   ▼
┌─────────────────────────┐
│    Oracle Cloud ARM      │
│    4 OCPU · 24 GB RAM    │
│                          │
│  ┌─────────┐             │
│  │  Nginx  │ :80/:443    │
│  │  (TLS)  │             │
│  └────┬────┘             │
│       │                  │
│  ┌────▼────┐  ┌────────┐ │
│  │ Frontend │  │ Static │ │
│  │ React   │  │ /dist  │ │
│  └─────────┘  └────────┘ │
│       │                  │
│  ┌────▼─────────────────┐│
│  │  FastAPI :8000       ││
│  │  + PyTorch (CPU)     ││
│  │  + ADFormerHybrid    ││
│  │  + Ensemble 5 models ││
│  └──────────────────────┘│
└─────────────────────────┘
```
