"""
patient-classification-alz.py

Etape 2 du pipeline Alzheimer : Classification du STADE (Début / Modéré / Avancé)

Licence : Creative Commons BY-NC-SA 4.0
Auteurs :
    - Kocupyr Romain (chef de projet) : rkocupyr@gmail.com
    - Multi_gpt_api (OpenAI)
    - Grok3
"""

import os, sys, uuid, h5py, torch, math, random
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import time
import qrcode
from fpdf import FPDF
import datetime
import argparse
from collections import Counter
from joblib import load
from torch.utils.data import Dataset
import torch.nn.functional as F
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import accuracy_score, f1_score, confusion_matrix, recall_score
from scipy.signal import welch
from scipy.stats import iqr, entropy as calc_entropy
import antropy as ant
from pykalman import KalmanFilter
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ALZ_ROOT = os.path.abspath(os.path.join(BASE_DIR, '..'))
if ALZ_ROOT not in sys.path:
    sys.path.insert(0, ALZ_ROOT)

from adformer_hybrid_voting_full import ADFormerHybrid
from eeg_io import load_eeg_data

start_time = time.time()

# === PARAMÈTRES GLOBAUX
fs = 128
samples = 512
num_electrodes = 19
patch_len = 64
num_patches = samples // patch_len
RAW_SIZE = samples * num_electrodes
FEATURE_SIZE = 267
TOTAL_FEATURE_SIZE = RAW_SIZE + FEATURE_SIZE
MODEL_FEATURE_DIM = FEATURE_SIZE
REJECTION_THRESHOLD = 0.7
ENTROPY_THRESHOLD = 0.9 * math.log(3)
asym_pairs = [(3, 5), (13, 15), (0, 1)]
bands = {
    'Delta': (0.5, 4), 'Theta': (4, 8), 'Alpha1': (8, 10),
    'Alpha2': (10, 13), 'Beta1': (13, 20), 'Beta2': (20, 30), 'Gamma': (30, 45)
}

kf_model = KalmanFilter(initial_state_mean=0, n_dim_obs=1)

device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

# === ARGUMENTS CLI
parser = argparse.ArgumentParser()
parser.add_argument("--patient_dir", required=True, help="Dossier du patient contenant l'EEG")
parser.add_argument("--model_dir", default="desktop/depistage", help="Dossier des modèles staging + scalers")
parser.add_argument("--output", default="results_positifs", help="Dossier de sortie pour le rapport")
parser.add_argument("--openbci_fs", type=float, default=250.0, help="Fréquence OpenBCI source (csv/txt) si timestamp absent")
args = parser.parse_args()

# === TROUVER FICHIER EEG
exts = [".set", ".edf", ".bdf", ".vhdr", ".fif", ".csv", ".txt"]
eeg_file = None
for file in os.listdir(args.patient_dir):
    if any(file.endswith(ext) for ext in exts):
        eeg_file = os.path.join(args.patient_dir, file)
        break
if eeg_file is None:
    raise FileNotFoundError("❌ Aucun fichier EEG trouvé dans le dossier du patient")

patient_id = os.path.basename(args.patient_dir)
save_dir = os.path.join(args.output, patient_id)
os.makedirs(save_dir, exist_ok=True)

# === CHARGEMENT EEG
data = load_eeg_data(
    eeg_file,
    target_fs=fs,
    target_channels=num_electrodes,
    openbci_fs=args.openbci_fs,
)


# === FEATURE ENGINEERING

def kalman_filter_signal(signal):
    """Applique un Filtre de Kalman 1D sur un signal (vector)."""
    filtered, _ = kf_model.filter(signal[:, None])
    return filtered[:, 0]

def extract_features(data):
    """
    Calcule un vecteur de features pour un segment EEG de forme (512, 19).
    Retourne environ 267 valeurs (selon ce qui est concaténé).
    """
    if data.shape != (samples, num_electrodes):
        raise ValueError(f"Segment shape invalide : {data.shape}")

    # Statistiques temporelles
    mean_t = np.mean(data, axis=0)     # 19
    var_t = np.var(data, axis=0)       # 19
    iqr_t = iqr(data, axis=0)          # 19

    # PSD via Welch
    freqs, psd = welch(data, fs=fs, nperseg=samples, axis=0)  # psd shape : (nfreqs, 19)

    band_feats = []
    kalman_means = []
    kalman_diffs = []

    # Calcul de la puissance moyenne dans chaque bande + Kalman
    for fmin, fmax in bands.values():
        idx = (freqs >= fmin) & (freqs <= fmax)
        raw_power = np.mean(psd[idx], axis=0)
        kalman_power = kalman_filter_signal(psd[idx].mean(axis=1))
        band_feats.append(raw_power)
        kalman_means.append(np.mean(kalman_power))
        kalman_diffs.append(raw_power.mean() - np.mean(kalman_power))

    rbp = np.stack(band_feats, axis=0)

    # Entropies (Permutation, Sample)
    perm_en = np.array([ant.perm_entropy(data[:, i], order=3, normalize=True)
                        for i in range(num_electrodes)])  # 19
    sample_en = np.array([ant.sample_entropy(data[:, i], order=2)
                          for i in range(num_electrodes)])  # 19

    # Mesures de connectivité / graph
    corr_matrix = np.corrcoef(data.T)
    clustering = np.array([
        np.sum(corr_matrix[i] > 0.5) / (num_electrodes - 1)
        for i in range(num_electrodes)
    ])  # 19
    path_length = np.mean(np.abs(corr_matrix))
    non_zero_corr = corr_matrix[np.abs(corr_matrix) > 0]
    efficiency = np.mean(1 / np.abs(non_zero_corr)) if len(non_zero_corr) > 0 else 0.0
    small_worldness = np.mean(clustering) / path_length if path_length != 0 else 0.0

    # Asymétries inter-hémisphériques
    asym = np.array([np.mean(data[:, i] - data[:, j]) for i, j in asym_pairs])  # 3

    # Concaténation finale
    features = np.concatenate([
        mean_t,                # 19
        var_t,                 # 19
        iqr_t,                 # 19
        rbp.flatten(),         # 7*19 = 133
        perm_en,               # 19
        sample_en,             # 19
        clustering,            # 19
        asym,                  # 3
        [path_length, efficiency, small_worldness],  # 3
        kalman_means,          # 7
        kalman_diffs           # 7
    ])
    return features  # ~267 valeurs

# === SEGMENTATION + BUILD H5
def build_h5_patient(data, save_path, patient_id):
    """
    Découpe un EEG en segments + calcule features + export H5 (pour patient unique)
    """
    segments = [data[i*samples:(i+1)*samples] for i in range(data.shape[0] // samples)]
    X_all = [np.concatenate([s.flatten(), extract_features(s)]) for s in segments]
    X_all = np.array(X_all)

    h5_path = os.path.join(save_dir, f"{patient_id}_positif.h5")
    with h5py.File(h5_path, 'w') as f:
        f.create_dataset("X", data=X_all)
        f.create_dataset("y", data=np.array([999]*len(X_all)))
        f.create_dataset("subj", data=np.array([patient_id.encode()] * len(X_all)))
    print(f"💾 Fichier .h5 généré : {save_path} pour {patient_id}")


# === DATASET POUR INFERENCE
class EEGHybridEvalDataset(Dataset):
    """
    Dataset d'inférence pour staging Alzheimer (3 classes)
    """
    def __init__(self, h5_path, patch_len=64):
        self.h5 = h5py.File(h5_path, 'r')
        self.X = self.h5["X"][:]
        self.y = self.h5["y"][:] if "y" in self.h5 else np.array([999] * len(self.X))

        self.patch_len = patch_len
        self.num_patches = samples // patch_len
        self.channels = num_electrodes
        self.scaler = StandardScaler().fit(self.X)

    def __len__(self):
        return len(self.X)

    def __getitem__(self, idx):
        full_feat = self.X[idx]
        label = int(self.y[idx]) - 1  # 🔥 conversion en 0/1/2 comme à l'entraînement

        raw_part = full_feat[:RAW_SIZE]
        eeg = raw_part.reshape(samples, self.channels)
        eeg = (eeg - eeg.mean(axis=0)) / (eeg.std(axis=0) + 1e-6)

        patch = eeg.reshape(self.num_patches, self.patch_len, self.channels)
        patch = patch.transpose(0, 2, 1).reshape(self.num_patches, -1)
        patch = torch.tensor(patch, dtype=torch.float32)

        scaled_full = self.scaler.transform([full_feat])[0]
        scaled_features = scaled_full[RAW_SIZE:]
        feat = torch.tensor(scaled_features, dtype=torch.float32)

        y = torch.tensor(label, dtype=torch.long)
        return patch, feat, y


inf_start = time.time()

# === CHARGEMENT DES MODELES STAGING (3 CLASSES)
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
models, scalers = [], []
for i in range(1, 6):
    model_path = f"{args.model_dir}/adformer_id_c_scaler_v{i}.pth"
    scaler_path = f"{args.model_dir}/adformer_id_c_scaler_v{i}_scaler.pkl"

    try:
        # Essai de charger un state_dict uniquement (safe)
        state_dict = torch.load(model_path, map_location=device, weights_only=True)
        m = ADFormerHybrid(num_classes=3).to(device)
        m.load_state_dict(state_dict)
        print(f"[V{i}] Modèle chargé via state_dict")
    except Exception:
        # Fallback : charge le modèle complet (moins safe → warning affiché)
        m = torch.load(model_path, map_location=device, weights_only=False)
        m = m.to(device)
        print(f"[V{i}] Modèle complet chargé")

    m.eval()
    models.append(m)

    scaler = load(scaler_path)
    scalers.append(scaler)

# === PREDICTION SEGMENTS
h5_output_path = os.path.join(save_dir, f"{patient_id}_positif.h5")
build_h5_patient(data, h5_output_path, patient_id=patient_id)

ds = EEGHybridEvalDataset(h5_output_path)
softmax_all = []

for model, scaler in zip(models, scalers):
    X_scaled = scaler.transform(ds.X)
    for i in range(len(ds)):
        patch, feat, y = ds[i]
        patch = patch.unsqueeze(0).to(device)
        feat_scaled = torch.tensor(X_scaled[i][RAW_SIZE:], dtype=torch.float32).unsqueeze(0).to(device)

        with torch.no_grad():
            logits = model(patch, feat_scaled)
            softmax = F.softmax(logits, dim=1).cpu().numpy()[0]
            softmax_all.append(softmax)


# === COMBINAISON DES PRÉDICTIONS
probs_mean = np.array(softmax_all).reshape(len(ds), 5, 3).mean(axis=1)
preds = np.argmax(probs_mean, axis=1)
confidences = np.max(probs_mean, axis=1)
entropies = [calc_entropy(p) for p in probs_mean]

inf_time = time.time() - inf_start
print(f"⚡ Temps d'inférence IA (modèles uniquement) : {inf_time:.2f} secondes")


# === IA DE CONFIANCE (softmax + entropie)
accepted = [(p, c) for p, c, e in zip(preds, confidences, entropies)
            if c >= REJECTION_THRESHOLD and e <= ENTROPY_THRESHOLD]
accepted_softmax = confidences

if accepted:
    pred_final = Counter([p for p, _ in accepted]).most_common(1)[0][0]
    conf_final = np.mean([c for _, c in accepted])
    diagnostic = ["Début", "Modéré", "Avancé"][pred_final]
else:
    pred_final = -1
    conf_final = 0.0
    diagnostic = "Inconnu"

# === VERDICT FINAL IA
if diagnostic == "Début":
    final_verdict = "🧠 Stade Alzheimer estimé : DÉBUT"
elif diagnostic == "Modéré":
    final_verdict = "🧠 Stade Alzheimer estimé : MODÉRÉ"
elif diagnostic == "Avancé":
    final_verdict = "🧠 Stade Alzheimer estimé : AVANCÉ"
else:
    final_verdict = "⚠️ Impossible d'estimer un stade Alzheimer (pas assez de segments fiables)"

# === VOTE SEGMENTAIRE (sur les acceptés)
count = Counter([p for p, _ in accepted])
nb_0 = count.get(0, 0)
nb_1 = count.get(1, 0)
nb_2 = count.get(2, 0)
total_accepted = nb_0 + nb_1 + nb_2

# === XAI
with torch.no_grad():
    patch, feat, y = ds[0]
    encoded = models[0].feature_encoder(feat.unsqueeze(0).to(device)).cpu().numpy().flatten()
top10_idx = np.argsort(-np.abs(encoded))[:10]
top10_vals = encoded[top10_idx]
top10_names = [f"F{i}" for i in top10_idx]

with open(os.path.join(save_dir, "xai_top10.csv"), "w") as f:
    f.write("Feature,Activation\n")
    for name, val in zip(top10_names, top10_vals):
        f.write(f"{name},{val:.4f}\n")

plt.figure(figsize=(8, 4))
plt.bar(top10_names, top10_vals, color='orange')
plt.title(f"Top 10 features - Stade : {diagnostic}")
plt.tight_layout()
plt.savefig(os.path.join(save_dir, "xai_top10.png"))
plt.close()

# === EXPORT TXT
rapport_path = os.path.join(save_dir, "rapport_staging.txt")
with open(rapport_path, "w") as f:
    f.write("=== Rapport IA - Classification Stade Alzheimer ===\n")
    f.write(f"Patient ID : {patient_id}\n")
    f.write(f"EEG : {eeg_file}\n")
    f.write(f"Total segments : {len(ds)}\n")
    f.write(f"Confiance IA (tous segments softmax) : {np.mean(confidences)*100:.2f}%\n")
    f.write(f"Confiance IA (segments filtrés) : {conf_final*100:.2f}%\n")
    f.write(f"Taux de rejet (softmax + entropie) : {(1 - len(accepted)/len(ds))*100:.2f}%\n")
    f.write(f"🧠 Diagnostic IA : {diagnostic}\n\n")

    if total_accepted > 0:
        f.write("--- Répartition des segments filtrés ---\n")
        f.write(f"Classe 0 (Début)   : {nb_0}\n")
        f.write(f"Classe 1 (Modéré)  : {nb_1}\n")
        f.write(f"Classe 2 (Avancé)  : {nb_2}\n")
        f.write(f"Pourcentage avancé : {(nb_2 / total_accepted) * 100:.2f}%\n")
    f.write("\n" + final_verdict + "\n")
    f.write(f"\n⏱️ Temps d'inférence IA : {inf_time:.2f} secondes\n")

# === RAPPORT .PDF
def generate_patient_pdf(patient_id, diagnostic, conf_final, taux_rejet, xai_top10_path, xai_graph_path, output_dir, mode="binaire", staging_diag=None, nb_0=0, nb_1=0, nb_2=0):
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)

    # === Génération QR code (UUID + horodatage)
    qr_code_id = str(uuid.uuid4())[:8]
    qr_text = f"Rapport validé | Patient : {patient_id} | ID : {qr_code_id} | {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"

    qr = qrcode.make(qr_text)
    qr_path = os.path.join(output_dir, f"qr_signature_{patient_id}.png")
    qr.save(qr_path)


    pdf.add_page()
    pdf.set_font("Arial", "B", 14)
    pdf.cell(0, 10, f"🧠 Rapport IA – Dépistage Alzheimer ({mode.upper()})", ln=True)
    pdf.set_font("Arial", size=11)
    pdf.cell(0, 10, f"Patient ID : {patient_id}", ln=True)
    pdf.cell(0, 10, f"Date : {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", ln=True)
    pdf.cell(0, 10, f"Diagnostic IA : {diagnostic}", ln=True)
    pdf.cell(0, 10, f"Confiance IA : {conf_final*100:.2f}%", ln=True)
    pdf.cell(0, 10, f"Taux de rejet : {taux_rejet:.2f}%", ln=True)

    if mode == "staging" and staging_diag is not None:
        pdf.ln(5)
        pdf.set_font("Arial", "B", 12)
        pdf.cell(0, 10, f"🔎 Stade Alzheimer détecté : {staging_diag}", ln=True)
        pdf.set_font("Arial", size=11)
        total = nb_0 + nb_1 + nb_2
        if total > 0:
            pdf.cell(0, 10, f"Répartition segments : Début={nb_0}, Modéré={nb_1}, Avancé={nb_2}", ln=True)
            pct_avance = (nb_2 / total) * 100
            pdf.cell(0, 10, f"Pourcentage segments avancés : {pct_avance:.2f}%", ln=True)

    # === Page XAI
    pdf.add_page()
    pdf.set_font("Arial", "B", 12)
    pdf.cell(0, 10, "Top 10 des features activées (XAI)", ln=True)
    try:
        pdf.image(xai_graph_path, w=180)
    except:
        pdf.cell(0, 10, f"[⚠️ Erreur lors du chargement du graphique XAI]", ln=True)

    pdf.set_font("Arial", size=10)
    try:
        with open(xai_top10_path, 'r') as f:
            lines = f.readlines()[1:]  # ignore header
            for line in lines:
                pdf.cell(0, 8, line.strip(), ln=True)
    except:
        pdf.cell(0, 10, "[⚠️ Erreur lors du chargement du CSV XAI]", ln=True)

    # === Signature dynamique IA
    pdf.add_page()
    pdf.set_font("Arial", "B", 12)
    pdf.cell(0, 10, "🔒 Signature électronique IA", ln=True)
    pdf.set_font("Arial", size=10)
    pdf.cell(0, 10, f"Rapport généré automatiquement par AlzheimerNet", ln=True)
    pdf.cell(0, 10, f"ID de validation : {qr_code_id}", ln=True)
    pdf.cell(0, 10, f"Date/Heure : {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", ln=True)

    try:
        pdf.image(qr_path, x=10, y=pdf.get_y()+10, w=40)
    except:
        pdf.cell(0, 10, "[QR code non disponible]", ln=True)


    pdf.output(os.path.join(output_dir, f"rapport_global_{patient_id}.pdf"))
    print(f"📄 Rapport PDF généré : rapport_global_{patient_id}.pdf")


generate_patient_pdf(
    patient_id=patient_id,
    diagnostic=diagnostic,
    conf_final=conf_final,
    taux_rejet=taux_rejet,
    xai_top10_path=os.path.join(save_dir, "xai_top10.csv"),
    xai_graph_path=os.path.join(save_dir, "xai_top10.png"),
    output_dir=save_dir,
    mode="staging",
    staging_diag=diagnostic,
    nb_0=nb_0,
    nb_1=nb_1,
    nb_2=nb_2
)

# === CONSOLE 🧠
print("=== Rapport IA - Classification Stade Alzheimer ===\n")
print(f"Patient ID : {patient_id}\n")
print(f"EEG : {eeg_file}\n")
print(f"Total segments : {len(ds)}\n")
print(f"Confiance IA (tous segments softmax) : {np.mean(confidences)*100:.2f}%\n")
print(f"Confiance IA (segments filtrés) : {conf_final*100:.2f}%\n")
print(f"Taux de rejet (softmax + entropie) : {(1 - len(accepted)/len(ds))*100:.2f}%\n")
print(f"🧠 Diagnostic IA : {diagnostic}\n\n")

print("--- Répartition des segments filtrés ---\n")
print(f"Classe 0 (Début)   : {nb_0}\n")
print(f"Classe 1 (Modéré)  : {nb_1}\n")
print(f"Classe 2 (Avancé)  : {nb_2}\n")
print(f"Pourcentage avancé : {(nb_2 / total_accepted) * 100:.2f}%\n")


print(f"\n{final_verdict}")
print(f"📁 Rapport complet : {rapport_path}")


# === Logger global intelligent en CSV
log_path = "log_diagnostic_global.csv"
now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

# Calcul taux de rejet
taux_rejet = (1 - len(accepted)/len(ds))*100 if len(ds) > 0 else 100.0

# Enregistrement dans le log CSV
log_line = f"{now},{patient_id},{h5_output_path},{len(ds)},{diagnostic},{conf_final*100:.2f},{taux_rejet:.2f}\n"

# Ajoute l'en-tête si le fichier n'existe pas encore
if not os.path.exists(log_path):
    with open(log_path, "w") as f:
        f.write("Timestamp,PatientID,FichierH5,Segments,Diagnostic,Confiance(%),TauxRejet(%)\n")

# Ajoute la ligne du patient
with open(log_path, "a") as f:
    f.write(log_line)

print (f"📁 Sauvegarde log_diagnostic_global.csv")

total_time = time.time() - start_time
print(f"⏱️ Temps total du script : {total_time:.2f} secondes")

