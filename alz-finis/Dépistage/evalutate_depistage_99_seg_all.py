"""
evalutate_depistage_99_seg_all.py

Licence : Creative Commons BY-NC-SA 4.0

Auteurs :
    - Kocupyr Romain (Auteur)
    - Multi_gpt_api
"""


import os
import torch
import numpy as np
import h5py
import csv
import math
import argparse
import matplotlib.pyplot as plt
import pandas as pd
from collections import defaultdict, Counter
from sklearn.metrics import (
    accuracy_score, f1_score, confusion_matrix,
    classification_report, recall_score
)
from torch.utils.data import Dataset
from torch.nn import functional as F
from scipy.stats import entropy as calc_entropy
from sklearn.preprocessing import StandardScaler
from adformer_hybrid_voting_full import ADFormerHybrid, RAW_SIZE, FEATURE_SIZE


# === Arguments ===
parser = argparse.ArgumentParser()
parser.add_argument("--mode", choices=["soft", "hard", "both"], default="both",
                    help="Méthode de vote : soft = moyenne softmax | hard = vote majoritaire | both = comparaison")
parser.add_argument("--target_id", type=str, default=None,
                    help="ID patient à filtrer (ex: sub-003). Si None, évalue tous.")
args = parser.parse_args()

# === Config ===
MODEL_PATHS = [
    "adformer_depis_scaler_v1.pth",
    "adformer_depis_scaler_v2.pth",
    "adformer_depis_scaler_v3.pth",
    "adformer_depis_scaler_v4.pth",
    "adformer_depis_scaler_v5.pth"
]
H5_PATH = "/workspace/memory_os_ai/alz/eeg_data_alzheimer_depistage_loss_scaler.h5"
SAVE_DIR = "/workspace/memory_os_ai/ad_depistage_alz_scaler/"
XAI_PLOT_DIR = os.path.join(SAVE_DIR, "barplots_XAI")
os.makedirs(XAI_PLOT_DIR, exist_ok=True)

FEATURE_NAMES = [f"F{i}" for i in range(FEATURE_SIZE)]

REJECTION_THRESHOLD = 0.7
MAX_ENTROPY = math.log(3)
ENTROPY_THRESHOLD = 0.9 * MAX_ENTROPY


# === Dataset ===
class EEGHybridEvalDataset(Dataset):
    def __init__(self, h5_path):
        self.h5 = h5py.File(h5_path, 'r')
        self.X = self.h5["X"][:]
        self.y = self.h5["y"][:]
#        self.subject_ids = [f"{label}_{i//5}" for i, label in enumerate(self.y)]
        self.subject_ids = [s.decode() if isinstance(s, bytes) else s for s in self.h5["subj"][:]]
        self.scaler = StandardScaler().fit(self.X)

    def __len__(self):
        return len(self.X)

    def __getitem__(self, idx):
        full = self.X[idx]
        label = int(self.y[idx])
        raw = full[:RAW_SIZE]
        feat = full[RAW_SIZE:]
        eeg = raw.reshape(512, 19)
        eeg = (eeg - eeg.mean(0)) / (eeg.std(0) + 1e-6)
        patch = eeg.reshape(8, 64, 19).transpose(0, 2, 1).reshape(8, -1)
        patch = torch.tensor(patch, dtype=torch.float32)
        scaled_feat = self.scaler.transform([full])[0][RAW_SIZE:]
        feat = torch.tensor(scaled_feat, dtype=torch.float32)
        return patch, feat, label, self.subject_ids[idx]

# === Load models ===
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
models = []
#for path in MODEL_PATHS:
#    m = ADFormerHybrid(num_classes=2).to(device)
#    m.load_state_dict(torch.load(path,weights_only=False))
#    m.eval()
#    models.append(m)
for path in MODEL_PATHS:
    m = torch.load(path, weights_only=False)
    m = m.to(device)
    m.eval()
    models.append(m)

def ensemble_predict(models, patch, feat):
    preds = []
    for model in models:
        with torch.no_grad():
            logits = model(patch, feat)
            preds.append(F.softmax(logits, dim=1))
    return torch.stack(preds).mean(dim=0)

def ensemble_vote_majoritaire(models, patch, feat):
    votes = []
    for model in models:
        with torch.no_grad():
            logits = model(patch, feat)
            pred = torch.argmax(logits, dim=1).item()
            votes.append(pred)
    return Counter(votes).most_common(1)[0][0]

# === Evaluation + XAI ===
ds = EEGHybridEvalDataset(H5_PATH)
subject_preds = defaultdict(list)
subject_truth = {}
xai_summary = []

print(f"\n🚀 Lancement évaluation + XAI | Mode = {args.mode.upper()}")


# === Évaluation SEGMENT-LEVEL ALL ==
seg_preds_all, seg_labels_all = [], []

for i in range(len(ds)):
    patch, feat, label, sid = ds[i]
    if args.target_id is not None and not sid.startswith(args.target_id):
        continue
    patch = patch.unsqueeze(0).to(device)
    feat = feat.unsqueeze(0).to(device)

    with torch.no_grad():
        if args.mode in ["soft", "both"]:
            proba_soft = ensemble_predict(models, patch, feat).cpu().numpy()[0]
            pred_soft = np.argmax(proba_soft)

        if args.mode in ["hard", "both"]:
            pred_hard = ensemble_vote_majoritaire(models, patch, feat)
            proba_hard = [1.0]

        if args.mode == "soft":
            pred = pred_soft
            proba = proba_soft
        elif args.mode == "hard":
            pred = pred_hard
            proba = proba_hard
        else:
            pred = pred_soft
            proba = proba_soft

        # Enregistrement des prédictions segment-level
        seg_preds_all.append(pred)
        seg_labels_all.append(label)

        # XAI
        feats_encoded = models[0].feature_encoder(feat)
        activations = feats_encoded.cpu().numpy().flatten()
        top10_idx = np.argsort(-np.abs(activations))[:10]
        top10_names = [FEATURE_NAMES[i] for i in top10_idx]
        top10_values = activations[top10_idx]

    # Barplot XAI
    plt.figure(figsize=(8, 4))
    plt.bar(top10_names, top10_values, color='orange')
    plt.title(f"Top 10 features patient {sid} (prédit={pred})")
    plt.xticks(rotation=45)
    plt.ylabel("Activation MLP")
    plt.tight_layout()
    plt.savefig(os.path.join(XAI_PLOT_DIR, f"patient_{i:03d}.png"))
    plt.close()

    subject_preds[sid].append((pred, max(proba)))
    subject_truth[sid] = label
    xai_summary.append({
        "patient_id": sid,
        "true_label": label,
        "predicted_label": pred,
        "top_features": ", ".join(top10_names)
    })


# === Résultats SEGMENT-LEVEL ALL ===
print("\n📊 === Évaluation SEGMENT-LEVEL ALL ===")
acc_seg_all = accuracy_score(seg_labels_all, seg_preds_all)
f1_seg_all = f1_score(seg_labels_all, seg_preds_all, average='macro')
recall_seg_all = recall_score(
    [1 if x > 0 else 0 for x in seg_labels_all],
    [1 if x > 0 else 0 for x in seg_preds_all]
)
cm_seg_all = confusion_matrix(seg_labels_all, seg_preds_all)
print(f"✅ Accuracy : {acc_seg_all*100:.2f}%")
print(f"📈 F1 Macro : {f1_seg_all*100:.2f}%")
print(f"🧠 Sensibilité Alzheimer : {recall_seg_all*100:.2f}%")
print("📊 Matrice de confusion :\n", cm_seg_all)


# === Évaluation SEGMENT-LEVEL avec IA de confiance (après filtrage) ===
ds = EEGHybridEvalDataset(H5_PATH)
subject_preds = defaultdict(list)
subject_truth = {}
xai_summary = []

seg_preds_filtered, seg_labels_filtered = [], []
rejected_segments = []
accepted_segments = []

for i in range(len(ds)):
    patch, feat, label, sid = ds[i]
    if args.target_id is not None and not sid.startswith(args.target_id):
        continue

    patch = patch.unsqueeze(0).to(device)
    feat = feat.unsqueeze(0).to(device)

    with torch.no_grad():
        if args.mode in ["soft", "both"]:
            proba_soft = ensemble_predict(models, patch, feat).cpu().numpy()[0]
            pred_soft = np.argmax(proba_soft)
            conf = np.max(proba_soft)
            ent = calc_entropy(proba_soft)

            if conf < REJECTION_THRESHOLD or ent > ENTROPY_THRESHOLD:
                rejected_segments.append((sid, label, conf, ent))
                continue
            else:
                pred = pred_soft
                proba = proba_soft
                accepted_segments.append((sid, label, pred, conf, ent))

        elif args.mode == "hard":
            pred = ensemble_vote_majoritaire(models, patch, feat)
            proba = [1.0]

        seg_preds_filtered.append(pred)
        seg_labels_filtered.append(label)

        feats_encoded = models[0].feature_encoder(feat)
        activations = feats_encoded.cpu().numpy().flatten()
        top10_idx = np.argsort(-np.abs(activations))[:10]
        top10_names = [FEATURE_NAMES[i] for i in top10_idx]
        top10_values = activations[top10_idx]

    # Barplot XAI
    plt.figure(figsize=(8, 4))
    plt.bar(top10_names, top10_values, color='orange')
    plt.title(f"Top 10 features patient {sid} (prédit={pred})")
    plt.xticks(rotation=45)
    plt.ylabel("Activation MLP")
    plt.tight_layout()
    plt.savefig(os.path.join(XAI_PLOT_DIR, f"patient_{i:03d}.png"))
    plt.close()

    subject_preds[sid].append((pred, np.max(proba)))
    subject_truth[sid] = label
    xai_summary.append({
        "patient_id": sid,
        "true_label": label,
        "predicted_label": pred,
        "top_features": ", ".join(top10_names)
    })



# === Résultats SEGMENT-LEVEL (après filtrage) ===
acc_seg_filtered = accuracy_score(seg_labels_filtered, seg_preds_filtered)
f1_seg_filtered = f1_score(seg_labels_filtered, seg_preds_filtered, average='macro')
recall_seg_filtered = recall_score(
    [1 if x > 0 else 0 for x in seg_labels_filtered],
    [1 if x > 0 else 0 for x in seg_preds_filtered]
)
cm_seg_filtered = confusion_matrix(seg_labels_filtered, seg_preds_filtered)
print("\n📊 === SEGMENT-LEVEL (après filtrage) ===")
print(f"✅ Accuracy : {acc_seg_filtered*100:.2f}%")
print(f"📈 F1 Macro : {f1_seg_filtered*100:.2f}%")
print(f"🧠 Sensibilité Alzheimer : {recall_seg_filtered*100:.2f}%")
print("📊 Matrice de confusion :\n", cm_seg_filtered)

# === Rejet segments
suffix = f"_{args.mode}"
print("\n📉 IA de confiance :")
print(f"Total segments analysés : {len(seg_preds_filtered) + len(rejected_segments)}")
print(f"✅ Acceptés : {len(seg_preds_filtered)}")
print(f"❌ Rejetés : {len(rejected_segments)} ({(len(rejected_segments)/(len(seg_preds_filtered)+len(rejected_segments))*100):.2f}%)")


# === Vote par patient
y_true, y_pred, rejected = [], [], []

for sid, preds in subject_preds.items():
    preds_above = [p for p, prob in preds if prob >= 0.5]
    if len(preds_above) == 0:
        rejected.append(sid)
        continue
    final = Counter(preds_above).most_common(1)[0][0]
    y_pred.append(final)
    y_true.append(subject_truth[sid])

# === Scores globaux PATIENT
acc = accuracy_score(y_true, y_pred)
f1 = f1_score(y_true, y_pred, average='macro')
cm = confusion_matrix(y_true, y_pred)
recall = recall_score(
    [1 if x > 0 else 0 for x in y_true],
    [1 if x > 0 else 0 for x in y_pred]
)

print(f"\n📊 Résultats PATIENT-LEVEL ({args.mode.upper()})")
print(f"✅ Accuracy : {acc*100:.2f}%")
print(f"📈 F1 Macro : {f1*100:.2f}%")
print(f"🧠 Sensibilité Alzheimer : {recall*100:.2f}%")
print(f"❌ Patients rejetés : {len(rejected)} / {len(subject_preds)}")
print("📊 Matrice de confusion :\n", cm)


# === Export CSV rejetés
with open(os.path.join(SAVE_DIR, f"segments_rejetes{suffix}.csv"), "w") as f:
    f.write("subject_id,true_label,confidence,entropy\n")
    for sid, label, conf, ent in rejected_segments:
        f.write(f"{sid},{label},{conf:.4f},{ent:.4f}\n")

# === Histogramme softmax
plt.figure(figsize=(8, 4))
probas_all = [conf for _, _, _, conf, _ in accepted_segments]
plt.hist(probas_all, bins=30, color='skyblue', edgecolor='black')
plt.title("Distribution des confiances (segments acceptés)")
plt.xlabel("Softmax max")
plt.ylabel("Nombre de segments")
plt.tight_layout()
plt.savefig(os.path.join(SAVE_DIR, f"histogramme_confiance_segments{suffix}.png"))
plt.close()

# === Confusion matrices
plt.figure(figsize=(6, 5))
plt.imshow(cm, cmap="Blues", interpolation="nearest")
plt.title(f"Matrice de confusion PATIENT-LEVEL ({args.mode})")
plt.colorbar()
plt.xticks(ticks=[0,1], labels=["CN", "AD"])
plt.yticks(ticks=[0,1], labels=["CN", "AD"])
plt.tight_layout()
plt.savefig(os.path.join(SAVE_DIR, f"confusion_matrix_patient_level{suffix}.png"))
plt.close()

plt.figure(figsize=(6, 5))
plt.imshow(cm_seg_all, cmap="Blues", interpolation="nearest")
plt.title(f"Matrice de confusion SEGMENT-LEVEL-ALL ({args.mode})")
plt.colorbar()
plt.xticks(ticks=[0,1], labels=["CN", "AD"])
plt.yticks(ticks=[0,1], labels=["CN", "AD"])
plt.tight_layout()
plt.savefig(os.path.join(SAVE_DIR, f"confusion_matrix_segment_level_all{suffix}.png"))
plt.close()

plt.figure(figsize=(6, 5))
plt.imshow(cm_seg_filtered, cmap="Blues", interpolation="nearest")
plt.title(f"Matrice de confusion SEGMENT-LEVEL-FILTERED ({args.mode})")
plt.colorbar()
plt.xticks(ticks=[0,1], labels=["CN", "AD"])
plt.yticks(ticks=[0,1], labels=["CN", "AD"])
plt.tight_layout()
plt.savefig(os.path.join(SAVE_DIR, f"confusion_matrix_segment_level_filtered{suffix}.png"))
plt.close()

# === Export CSV + TXT
pd.DataFrame(xai_summary).to_csv(os.path.join(SAVE_DIR, f"xai_summary{suffix}.csv"), index=False)

with open(os.path.join(SAVE_DIR, f"classification_report{suffix}.txt"), "w") as f:
    f.write(f"== Alzheimer EEG Classifier - MODE {args.mode.upper()} ==\n\n")
    f.write("---- PATIENT LEVEL ----\n")
    f.write(f"Accuracy: {acc*100:.2f}%\n")
    f.write(f"F1 Macro: {f1*100:.2f}%\n")
    f.write(f"Recall Alzheimer: {recall*100:.2f}%\n")
    f.write(f"Patients rejetés : {len(rejected)} / {len(subject_preds)}\n")
    f.write("Matrice de confusion :\n")
    f.write(np.array2string(cm))

    f.write("\n\n---- SEGMENT LEVEL (ALL) ----\n")
    f.write(f"Accuracy: {acc_seg_all*100:.2f}%\n")
    f.write(f"F1 Macro: {f1_seg_all*100:.2f}%\n")
    f.write(f"Recall Alzheimer: {recall_seg_all*100:.2f}%\n")
    f.write("Matrice de confusion :\n")
    f.write(np.array2string(cm_seg_all))

    f.write("\n\n---- SEGMENT LEVEL (filtré) ----\n")
    f.write(f"Accuracy: {acc_seg_filtered*100:.2f}%\n")
    f.write(f"F1 Macro: {f1_seg_filtered*100:.2f}%\n")
    f.write(f"Recall Alzheimer: {recall_seg_filtered*100:.2f}%\n")
    f.write("Matrice de confusion :\n")
    f.write(np.array2string(cm_seg_filtered))

    f.write("\n\n==== COMPARATIF SEGMENT ====\n")
    f.write(f"Gain Accuracy : {acc_seg_filtered - acc_seg_all:.4f}\n")
    f.write(f"Gain F1 Macro : {f1_seg_filtered - f1_seg_all:.4f}\n")
    f.write(f"Gain Recall AD : {recall_seg_filtered - recall_seg_all:.4f}\n")


print(f"✅ Rapport IA de confiance généré : {SAVE_DIR}")
if args.target_id:
    print(f"🧠 Rapport généré uniquement pour le patient : {args.target_id}")

