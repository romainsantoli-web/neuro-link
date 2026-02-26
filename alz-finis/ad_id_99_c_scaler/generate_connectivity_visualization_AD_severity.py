import os
import argparse
import numpy as np
import h5py
import matplotlib.pyplot as plt
import seaborn as sns
import pandas as pd
import networkx as nx

# === Configs
GROUP_LABELS = {
    1: "Léger",
    2: "Modéré",
    3: "Sévère"
}
NUM_ELECTRODES = 19

# === Args
parser = argparse.ArgumentParser()
parser.add_argument(
    "--h5",
    default="/workspace/memory_os_ai/alz/eeg_data_alzheimer_99_id_C_scaler.h5",
    help="Fichier .h5 à analyser (par défaut : %(default)s)"
)
parser.add_argument("--group", choices=["Léger", "Modéré", "Sévère", "Tous"], default="Tous",
                    help="Groupe à analyser (Léger, Modéré, Sévère, Tous)")
parser.add_argument("--outdir", default="/workspace/memory_os_ai/ad_id_99_c_scaler", help="Dossier de sortie")
args = parser.parse_args()

os.makedirs(args.outdir, exist_ok=True)

# === Load HDF5
print(f"📂 Chargement du fichier : {args.h5}")
with h5py.File(args.h5, 'r') as f:
    X = f["X"][:]
    y = f["y"][:]
    subj = f["subj"][:]

    X_raw = X[:, :NUM_ELECTRODES * 512]  # brut EEG uniquement

# === Sélection du groupe
print(f"🎯 Groupe sélectionné : {args.group}")
GROUP_MAP = {
    "Léger": [1],
    "Modéré": [2],
    "Sévère": [3],
    "Tous": [1, 2, 3]
}

selected_idx = [i for i in range(len(y)) if y[i] in GROUP_MAP[args.group]]
print(f"📊 Labels présents : {set(y[i] for i in selected_idx)}")

if not selected_idx:
    print("❌ Aucun patient trouvé pour ce groupe.")
    exit()

# === Calcul des matrices
print(f"🔄 Calcul de la connectivité moyenne sur {len(selected_idx)} segments...")
all_corr = []

for i in selected_idx:
    seg = X_raw[i].reshape(512, NUM_ELECTRODES)
    corr = np.corrcoef(seg.T)
    all_corr.append(corr)

mean_corr = np.mean(all_corr, axis=0)

# === Export CSV
csv_path = os.path.join(args.outdir, f"connectivity_summary_{args.group}.csv")
pd.DataFrame(mean_corr).to_csv(csv_path, index=False)
print(f"✅ Matrice moyenne sauvegardée : {csv_path}")

# === Heatmap corrélation
plt.figure(figsize=(8, 6))
sns.heatmap(mean_corr, annot=False, cmap="coolwarm", vmin=-1, vmax=1)
plt.title(f"Matrice de corrélation - Groupe {args.group}")
plt.tight_layout()
plt.savefig(os.path.join(args.outdir, f"connectivity_corr_matrix_{args.group}.png"))
plt.close()

# === Graphe de connectivité (seuil > 0.5)
threshold = 0.5
G = nx.Graph()

for i in range(NUM_ELECTRODES):
    for j in range(i+1, NUM_ELECTRODES):
        if mean_corr[i, j] > threshold:
            G.add_edge(i, j, weight=mean_corr[i, j])

plt.figure(figsize=(6, 6))
pos = nx.spring_layout(G, seed=42)
nx.draw(G, pos, with_labels=True, node_color="skyblue", node_size=600, edge_color="gray")
plt.title(f"Graphe de connectivité EEG - {args.group} (r > {threshold})")
plt.tight_layout()
plt.savefig(os.path.join(args.outdir, f"connectivity_graph_{args.group}.png"))
plt.close()

print(f"🧠 Graphe sauvegardé : {args.outdir}/connectivity_graph_{args.group}.png")

# === Done
print("🎉 Analyse de connectivité terminée !")
