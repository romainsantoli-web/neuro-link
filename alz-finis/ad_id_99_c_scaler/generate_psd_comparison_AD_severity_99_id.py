# === BLOC 1 ===
import os
import h5py
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import pandas as pd
from scipy.signal import welch
from argparse import ArgumentParser
from openpyxl import Workbook
from openpyxl.utils.dataframe import dataframe_to_rows

# === PARAMS
parser = ArgumentParser()
parser.add_argument(
    "--h5",
    default="/workspace/memory_os_ai/alz/eeg_data_alzheimer_99_id_C_scaler.h5",
    help="Fichier .h5 à analyser (par défaut : %(default)s)"
)
parser.add_argument("--group", choices=["AD", "Léger", "Modéré", "Sévère", "Tous"], default="Tous", help="Filtrage du groupe à analyser")
parser.add_argument("--outdir", default="/workspace/memory_os_ai/ad_id_99_c_scaler", help="Dossier de sortie")

args = parser.parse_args()
os.makedirs(args.outdir, exist_ok=True)

# === CONST
FS = 128
SAMPLES = 512
NUM_ELECTRODES = 19
BANDS = {
    "Delta": (0.5, 4),
    "Theta": (4, 8),
    "Alpha": (8, 13),
    "Beta": (13, 30),
    "Gamma": (30, 45)
}

GROUP_MAP = {
    "Léger": [1],
    "Modéré": [2],
    "Sévère": [3],
    "AD": [2, 3],
    "Tous": [1, 2, 3]
}

# === LOAD DATA
print(f"📂 Chargement : {args.h5}")
with h5py.File(args.h5, 'r') as f:
    X = f["X"][:]
    y = f["y"][:]
X_raw = X[:, :SAMPLES * NUM_ELECTRODES].reshape(-1, SAMPLES, NUM_ELECTRODES)

# === BLOC 2 ===
def get_indices():
    return [i for i in range(len(y)) if y[i] in GROUP_MAP[args.group]]

indices = get_indices()
print(f"📊 Groupe sélectionné : {args.group}")
print(f"🎯 Nombre de segments : {len(indices)}")
print(f"🏷️ Labels présents : {set(y[i] for i in indices)}")

# === CONST
def compute_psd(segment):
    freqs, psd = welch(segment, fs=FS, axis=0, nperseg=256)
    powers = {}
    for band, (fmin, fmax) in BANDS.items():
        mask = (freqs >= fmin) & (freqs <= fmax)
        powers[band] = np.mean(psd[mask], axis=0)
    return powers

# === AGRÉGER PAR GROUPE
group_data = {band: [] for band in BANDS}
electrode_data = {band: [] for band in BANDS}

for i in indices:
    seg = X_raw[i]
    psd = compute_psd(seg)
    for band in BANDS:
        mean_band = np.mean(psd[band])
        group_data[band].append(mean_band)
        electrode_data[band].append(psd[band])  # shape (19,)

# === MOYENNE PAR ÉLECTRODE
electrode_avg = {band: np.mean(electrode_data[band], axis=0) for band in BANDS}
electrode_df = pd.DataFrame(electrode_avg)
electrode_df.columns.name = "Bande"
electrode_df.index.name = "Électrode"
electrode_df.to_csv(os.path.join(args.outdir, f"psd_electrode_{args.group}.csv"))

# === BLOC 3 ===

# Courbe moyenne par bande
mean_vals = [np.mean(group_data[band]) for band in BANDS]
plt.figure(figsize=(8, 5))
plt.plot(list(BANDS.keys()), mean_vals, marker='o', color='darkorange')
plt.title(f"Puissance EEG moyenne par bande - {args.group}")
plt.ylabel("Puissance moyenne")
plt.grid(True)
plt.tight_layout()
plt.savefig(os.path.join(args.outdir, f"psd_curve_{args.group}.png"))
plt.savefig(os.path.join(args.outdir, f"psd_curve_{args.group}.svg"))
plt.close()

# Boxplot
df_all = pd.DataFrame()
for band in BANDS:
    df_all = pd.concat([
        df_all,
        pd.DataFrame({
            "Puissance": group_data[band],
            "Bande": band,
            "Groupe": args.group
        })
    ])
plt.figure(figsize=(10, 6))
sns.boxplot(data=df_all, x="Bande", y="Puissance", palette="Set2")
plt.title(f"Boxplot EEG par bande - {args.group}")
plt.tight_layout()
plt.savefig(os.path.join(args.outdir, f"psd_boxplot_{args.group}.png"))
plt.savefig(os.path.join(args.outdir, f"psd_boxplot_{args.group}.svg"))
plt.close()

# XLSX export
xlsx_path = os.path.join(args.outdir, f"psd_report_{args.group}.xlsx")
wb = Workbook()
ws1 = wb.active
ws1.title = f"{args.group}_global"
for r in dataframe_to_rows(pd.DataFrame(group_data), index=False, header=True):
    ws1.append(r)

ws2 = wb.create_sheet(title=f"{args.group}_electrodes")
for r in dataframe_to_rows(electrode_df, index=True, header=True):
    ws2.append(r)

wb.save(xlsx_path)
print(f"📁 Export Excel : {xlsx_path}")
print("✅ Rapport PSD GOLD terminé 🧠📈")
