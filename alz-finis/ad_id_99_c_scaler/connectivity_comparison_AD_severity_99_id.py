import os
import numpy as np
import h5py
import matplotlib.pyplot as plt
import seaborn as sns
import pandas as pd
import networkx as nx

# === CONFIG
H5_PATH = "/workspace/memory_os_ai/alz/eeg_data_alzheimer_99_id_C_scaler.h5"
OUTDIR = "/workspace/memory_os_ai/ad_id_99_c_scaler"
NUM_ELECTRODES = 19
SEGMENT_LENGTH = 512
THRESHOLD = 0.5

os.makedirs(OUTDIR, exist_ok=True)

# === CHARGEMENT DATASET
with h5py.File(H5_PATH, 'r') as f:
    X = f["X"][:]
    y = f["y"][:]
    subj = f["subj"][:]

X_raw = X[:, :NUM_ELECTRODES * SEGMENT_LENGTH]

# === GROUPE INDEX
idx_leg = [i for i in range(len(y)) if y[i] == 1]
idx_mod = [i for i in range(len(y)) if y[i] == 2]
idx_sev = [i for i in range(len(y)) if y[i] == 3]


print(f"✅ {len(idx_leg)} segments Léger | {len(idx_mod)} segments Modéré | {len(idx_sev)} segments Sevère")

def compute_mean_corr(index_list):
    corrs = []
    for i in index_list:
        seg = X_raw[i].reshape(SEGMENT_LENGTH, NUM_ELECTRODES)
        corr = np.corrcoef(seg.T)
        corrs.append(corr)
    return np.mean(corrs, axis=0)

mean_corr_leg = compute_mean_corr(idx_leg)
mean_corr_mod = compute_mean_corr(idx_mod)
mean_corr_sev = compute_mean_corr(idx_sev)

# === EXPORT CSV
pd.DataFrame(mean_corr_leg).to_csv(os.path.join(OUTDIR, "connectivity_matrix_leg.csv"), index=False)
pd.DataFrame(mean_corr_mod).to_csv(os.path.join(OUTDIR, "connectivity_matrix_mod.csv"), index=False)
pd.DataFrame(mean_corr_sev).to_csv(os.path.join(OUTDIR, "connectivity_matrix_sev.csv"), index=False)

# === HEATMAP COMPARATIVE
plt.figure(figsize=(18, 5))
plt.subplot(1, 3, 1)
sns.heatmap(mean_corr_leg, cmap="coolwarm", vmin=-1, vmax=1)
plt.title("Léger - Corrélation EEG")

plt.subplot(1, 3, 2)
sns.heatmap(mean_corr_mod, cmap="coolwarm", vmin=-1, vmax=1)
plt.title("Modéré - Corrélation EEG")

plt.subplot(1, 3, 3)
sns.heatmap(mean_corr_sev, cmap="coolwarm", vmin=-1, vmax=1)
plt.title("Sévère - Corrélation EEG")

plt.tight_layout()
plt.savefig(os.path.join(OUTDIR, "connectivity_comparison_3groups.png"))
plt.savefig(os.path.join(OUTDIR, "connectivity_comparison_3groups.svg"))
plt.close()
print("📊 Heatmaps comparatives sauvegardées")


# === DISTRIBUTION MOYENNE CONNECTIVITÉ
mean_leg = np.mean(mean_corr_leg[np.triu_indices(NUM_ELECTRODES, 1)])
mean_mod = np.mean(mean_corr_mod[np.triu_indices(NUM_ELECTRODES, 1)])
mean_sev = np.mean(mean_corr_sev[np.triu_indices(NUM_ELECTRODES, 1)])


df_comp = pd.DataFrame({
    "Groupe": (
        ["Léger"] * len(idx_leg) +
        ["Modéré"] * len(idx_mod) +
        ["Sévère"] * len(idx_sev)
    ),
    "Moyenne Connectivité": [
        np.mean(np.corrcoef(X_raw[i].reshape(SEGMENT_LENGTH, NUM_ELECTRODES).T)[np.triu_indices(NUM_ELECTRODES, 1)])
        for i in idx_leg + idx_mod + idx_sev
    ]
})

plt.figure(figsize=(6, 5))
sns.boxplot(data=df_comp, x="Groupe", y="Moyenne Connectivité", palette="pastel")
plt.title("Comparaison de la connectivité moyenne (3 niveaux de sévérité)")
plt.tight_layout()
plt.savefig(os.path.join(OUTDIR, "connectivity_distribution_boxplot.png"))
plt.savefig(os.path.join(OUTDIR, "connectivity_distribution_boxplot.svg"))
plt.close()
print("📈 Boxplot sauvegardé")


# === GRAPHES DE CONNECTIVITÉ
def plot_graph(mean_corr, group_name):
    G = nx.Graph()
    for i in range(NUM_ELECTRODES):
        for j in range(i+1, NUM_ELECTRODES):
            if mean_corr[i, j] > THRESHOLD:
                G.add_edge(i, j, weight=mean_corr[i, j])
    plt.figure(figsize=(6, 6))
    pos = nx.spring_layout(G, seed=42)
    nx.draw(G, pos, with_labels=True, node_color="lightblue", edge_color="gray")
    plt.title(f"Graphe de connectivité - {group_name}")
    plt.tight_layout()
    plt.savefig(os.path.join(OUTDIR, f"connectivity_graph_{group_name}.png"))
    plt.savefig(os.path.join(OUTDIR, f"connectivity_graph_{group_name}.svg"))
    plt.close()
    print(f"🌐 Graphe EEG {group_name} sauvegardé")

plot_graph(mean_corr_leg, "Léger")
plot_graph(mean_corr_mod, "Modéré")
plot_graph(mean_corr_sev, "Sévère")

print("🎯 Graphes de connectivité pour les 3 classes générés.")
