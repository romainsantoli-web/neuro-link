#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
🧠 Prédiction Alzheimer depuis un fichier EEG (.set)
Licence : Creative Commons BY-NC-SA 4.0
Auteurs :
    - Kocupyr Romain (Auteur)
    - Multi_gpt_api
"""

import os
import argparse
import sys
import numpy as np
import torch
import torch.nn.functional as F
import matplotlib.pyplot as plt
from sklearn.preprocessing import StandardScaler
from joblib import load

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ALZ_ROOT = os.path.abspath(os.path.join(BASE_DIR, '..'))
if ALZ_ROOT not in sys.path:
    sys.path.insert(0, ALZ_ROOT)

from adformer_hybrid_voting_full import ADFormerHybrid, RAW_SIZE, FEATURE_SIZE, extract_features
from eeg_io import load_eeg_data


# === PARAMÈTRES
fs = 128
samples = 512
num_electrodes = 19
patch_len = 64
num_patches = samples // patch_len

# === ARGUMENTS CLI
parser = argparse.ArgumentParser()
parser.add_argument("--file", required=True, help="Fichier EEG (.set, .edf, .vhdr, .fif, .csv, .txt)")
parser.add_argument("--openbci_fs", type=float, default=250.0, help="Fréquence OpenBCI source (csv/txt) si timestamp absent")
parser.add_argument(
    "--model",
    default="/workspace/memory_os_ai/adformer_id_c_scaler_v1.pth",
    help="Fichier .pth à analyser (par défaut : %(default)s)"
)
parser.add_argument(
    "--models",
    nargs="*",
    default=None,
    help="Liste de fichiers .pth pour ensemble voting (prioritaire sur --model)"
)
parser.add_argument(
    "--scaler",
    default="/workspace/memory_os_ai/adformer_id_c_scaler_v1_scaler.pkl",
    help="Fichier scaler .pkl (par défaut : %(default)s)"
)
parser.add_argument("--name", type=str, default="patient_X", help="Nom patient")
parser.add_argument("--mode", choices=["soft", "hard", "both"], default="both", help="Mode de prédiction")
parser.add_argument("--output", type=str, default="rapport_", help="Répertoire de sortie")
args = parser.parse_args()

# === Dossier résultat
save_dir = f"{args.output}{args.name}"
os.makedirs(save_dir, exist_ok=True)
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

# === Charger EEG
ext = os.path.splitext(args.file)[-1].lower()
print(f"📥 Chargement EEG ({ext})...")
data = load_eeg_data(
    args.file,
    target_fs=fs,
    target_channels=num_electrodes,
    openbci_fs=args.openbci_fs,
)

# === Découpage
nb_segments = data.shape[0] // samples
segments = [data[i*samples:(i+1)*samples] for i in range(nb_segments)]
if len(segments) == 0:
    raise ValueError("❌ Aucun segment exploitable trouvé.")
print(f"🧠 {len(segments)} segments extraits")

# === Feature extraction
X_all = []
for seg in segments:
    feat = extract_features(seg)
    combined = np.concatenate([seg.flatten(), feat])  # shape = (9995,)
    X_all.append(combined)
X_all = np.array(X_all)

# === Import scaler ou Normalisation si pas de scaler
if args.scaler and os.path.isfile(args.scaler):
    print(f"📊 Chargement du scaler : {args.scaler}")
    scaler = load(args.scaler)
else:
    print("⚠️ Aucun scaler fourni — recalcul sur le patient en cours")
    scaler = StandardScaler().fit(X_all)

X_scaled = scaler.transform(X_all)

# === Préparation des inputs modèle
patches = []
feats = []
for x in X_scaled:
    raw_part = x[:RAW_SIZE].reshape(samples, num_electrodes)
    feat_part = x[RAW_SIZE:]
    patch = raw_part.reshape(num_patches, patch_len, num_electrodes).transpose(0, 2, 1).reshape(num_patches, -1)
    patches.append(patch)
    feats.append(feat_part)
patches = torch.tensor(np.array(patches), dtype=torch.float32).to(device)
feats = torch.tensor(np.array(feats), dtype=torch.float32).to(device)

# === Charger modèle(s) — ensemble voting si --models fourni
def _load_model(path, device, num_classes=3):
    checkpoint = torch.load(path, map_location=device, weights_only=False)
    if isinstance(checkpoint, dict):
        m = ADFormerHybrid(num_classes=num_classes).to(device)
        m.load_state_dict(checkpoint)
    else:
        m = checkpoint.to(device)
    m.eval()
    return m

model_paths = args.models if args.models else [args.model]
models = [_load_model(p, device, num_classes=3) for p in model_paths]
print(f"🔧 {len(models)} modèle(s) chargé(s) {'(ensemble voting)' if len(models) > 1 else '(single)'}")

# === Prédictions
modes_to_run = ["soft", "hard"] if args.mode == "both" else [args.mode]

for mode in modes_to_run:
    print(f"\n🧠 Prédiction MODE = {mode.upper()}...")

    if mode == "soft":
        # Ensemble soft voting : moyenne des softmax de chaque modèle
        all_probs = []
        for m in models:
            with torch.no_grad():
                logits = m(patches, feats)
                probs = F.softmax(logits, dim=1).cpu().detach().numpy()
            all_probs.append(probs)
        avg_probs = np.mean(all_probs, axis=0)  # (n_segments, n_classes)
        preds = np.argmax(avg_probs, axis=1)
        pred_patient = np.bincount(preds).argmax()
        proba_patient = avg_probs.mean(axis=0)[pred_patient]
    else:  # hard
        # Ensemble hard voting : majorité sur les votes de tous les modèles
        all_preds = []
        for m in models:
            for i in range(len(patches)):
                with torch.no_grad():
                    logit = m(patches[i:i+1], feats[i:i+1])
                    pred = torch.argmax(logit, dim=1).item()
                    all_preds.append(pred)
        pred_patient = max(set(all_preds), key=all_preds.count)
        proba_patient = all_preds.count(pred_patient) / len(all_preds)

    diagnostic = ["Léger", "Modéré", "Sévère"][pred_patient]


    # === XAI (via feature encoder — moyenne des activations des modèles)
    with torch.no_grad():
        encoded_feats = []
        for m in models:
            enc = m.feature_encoder(feats.mean(0, keepdim=True)).cpu().numpy().flatten()
            encoded_feats.append(enc)
        encoded_feat = np.mean(encoded_feats, axis=0)
    top10_idx = np.argsort(-np.abs(encoded_feat))[:10]
    top10_values = encoded_feat[top10_idx]
    top10_names = [f"F{i}" for i in top10_idx]

    # === Sauvegardes
    # Barplot XAI
    plt.figure(figsize=(8, 4))
    plt.bar(top10_names, top10_values, color='orange')
    plt.title(f"Top 10 features - {args.name} ({mode})")
    plt.ylabel("Activation")
    plt.tight_layout()
    plt.savefig(os.path.join(save_dir, f"xai_top10_{args.name}_{mode}.png"))
    plt.close()

    # Rapport texte
    with open(os.path.join(save_dir, f"rapport_{args.name}_{mode}.txt"), "w") as f:
        f.write(f"=== Rapport IA Alzheimer ===\n\n")
        f.write(f"🧠 Patient: {args.name}\n")
        f.write(f"🧪 Mode : {mode}\n")
        f.write(f"🧬 Prédiction IA : {diagnostic} (classe {pred_patient})\n")
        f.write(f"📈 Confiance : {proba_patient*100:.2f}%\n")
        f.write(f"\nTop 10 features activées :\n")
        for name, val in zip(top10_names, top10_values):
            f.write(f"  {name} : {val:.4f}\n")

    # CSV XAI
    with open(os.path.join(save_dir, f"xai_top10_{args.name}_{mode}.csv"), "w") as f:
        f.write("Feature,Activation\n")
        for name, val in zip(top10_names, top10_values):
            f.write(f"{name},{val:.4f}\n")

    # Print console
    print(f"✅ MODE {mode.upper()} terminé")
    print(f"🔍 Diagnostic IA : {diagnostic} ({proba_patient*100:.2f}% confiance)")
    print(f"📊 Rapport : {os.path.join(save_dir, f'rapport_{args.name}_{mode}.txt')}")

print(f"\n✅ Tous les résultats disponibles dans : {save_dir}")

