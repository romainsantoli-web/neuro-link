#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
ADFormer-HYBRID — EEG Alzheimer Classifier (Full Pipeline, Stable Version)
Licence : Creative Commons BY-NC-SA 4.0
Auteurs : Kocupyr Romain
Dev : Gpt multi_gpt_api, Grok3
"""

import os
import numpy as np
import pandas as pd
import h5py
import mne
import joblib
import torch
import torch.nn as nn
import torch.nn.functional as F
from torch.optim import AdamW
from torch.utils.data import Dataset, DataLoader, Subset
from tqdm import tqdm
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split
from sklearn.svm import SVC
from scipy.signal import welch
from scipy.stats import iqr
from pykalman import KalmanFilter
import antropy as ant
from collections import Counter
import argparse
import random

# ====================================================================================
# === PARAMÈTRES GLOBAUX
# ====================================================================================
fs = 128               # Fréquence d'échantillonnage cible
samples = 512          # Taille (en échantillons) de chaque segment EEG
num_electrodes = 19    # Nombre d'électrodes retenues

# Nous allons stocker : 512*19 = 9728 points bruts + ~267 features
# Ajustons la taille finale attendue :
RAW_SIZE = samples * num_electrodes  # 512*19 = 9728
FEATURE_SIZE = 267                   # estimé après concaténation des features
TOTAL_FEATURE_SIZE = RAW_SIZE + FEATURE_SIZE  # ~ 9995

# Mise à jour : le modèle aura un feature_dim correspondant UNIQUEMENT à la partie "features".
MODEL_FEATURE_DIM = FEATURE_SIZE

# Paires d’asymétrie utilisées
asym_pairs = [(3, 5), (13, 15), (0, 1)]

# Gammes de fréquences
bands = {
    'Delta': (0.5, 4),
    'Theta': (4, 8),
    'Alpha1': (8, 10),
    'Alpha2': (10, 13),
    'Beta1': (13, 20),
    'Beta2': (20, 30),
    'Gamma': (30, 45)
}

# Modèle Kalman pour un lissage éventuel des puissances spectrales
kf_model = KalmanFilter(initial_state_mean=0, n_dim_obs=1)


# ====================================================================================
# === FONCTIONS DE GESTION DE SEED
# ====================================================================================
def set_seed(seed):
    """Fixe la seed pour une reproductibilité maximale."""
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)


# ====================================================================================
# === FONCTIONS DE FEATURE ENGINEERING
# ====================================================================================
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
        # Puissance brute moyenne (par canal) dans la bande
        raw_power = np.mean(psd[idx], axis=0)  # shape (19,)
        # Lissage Kalman sur la moyenne spectrale (moyenne sur les canaux, pour la courbe freq)
        kalman_power = kalman_filter_signal(psd[idx].mean(axis=1))  # shape (nb_freqs_in_band,)
        # On stocke
        band_feats.append(raw_power)
        kalman_means.append(np.mean(kalman_power))
        kalman_diffs.append(raw_power.mean() - np.mean(kalman_power))

    rbp = np.stack(band_feats, axis=0)  # shape (7, 19)

    # Entropies (Permutation, Sample)
    perm_en = np.array([ant.perm_entropy(data[:, i], order=3, normalize=True)
                        for i in range(num_electrodes)])  # 19
    sample_en = np.array([ant.sample_entropy(data[:, i], order=2)
                          for i in range(num_electrodes)])  # 19

    # Mesures de connectivité / graph
    corr_matrix = np.corrcoef(data.T)  # shape (19, 19)
    clustering = np.array([
        np.sum(corr_matrix[i] > 0.5) / (num_electrodes - 1)
        for i in range(num_electrodes)
    ])  # 19
    path_length = np.mean(np.abs(corr_matrix))
    non_zero_corr = corr_matrix[np.abs(corr_matrix) > 0]
    efficiency = np.mean(1 / np.abs(non_zero_corr)) if len(non_zero_corr) > 0 else 0.0
    small_worldness = np.mean(clustering) / path_length if path_length != 0 else 0.0

    # Asymétries inter-hémisphériques
    asym = np.array([np.mean(data[:, i] - data[:, j]) for i, j in asym_pairs])  # ex: 3 valeurs

    # Concaténation finale (environ 267 valeurs totales)
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

    return features  # ~ 267 valeurs


def get_label(row):
    """
    Classification binaire :
    - Group 'CN' => classe 0 (Non-Alzheimer)
    - Group 'A' ou 'AD' => classe 1 (Alzheimer)
    - Autres groupes => -1 (hors scope)
    """
    group = str(row["Group"]).strip().upper()

    if group in ["CN", "C"]:
        return 0  # Contrôle sain
    elif group in ["A", "AD"]:
        return 1  # Alzheimer
    else:
        return -1  # Hors scope


def build_h5(data_dir, h5_file):
    """
    Parcourt le répertoire BIDS, lit les EEG (.set), segmente, extrait (data brute + features),
    et stocke dans un dataset HDF5 "X" et "y".
    """
    print("📦 Création du dataset HDF5 propre...")

    # On lit le participants.tsv pour récupérer le groupe et le MMSE
    participants = pd.read_csv(os.path.join(data_dir, "participants.tsv"), sep="\t")
    subjects = participants[participants["Group"].isin(["A", "AD", "CN", "C"])]

    with h5py.File(h5_file, 'w') as f:
        # Création des datasets extensibles
        f.create_dataset(
            "X",
            shape=(0, TOTAL_FEATURE_SIZE),
            maxshape=(None, TOTAL_FEATURE_SIZE),
            dtype='float32'
        )
        f.create_dataset(
            "y",
            shape=(0,),
            maxshape=(None,),
            dtype='int32'
        )


        # Patient ID pour évaluation
        f.create_dataset(
            "subj",
            shape=(0,),
            maxshape=(None,),
            dtype=h5py.string_dtype(encoding='utf-8')
        )


        offset = 0
        for _, row in subjects.iterrows():
            pid = row["participant_id"]
            label = get_label(row)
            # On ignore si label invalide
#            if label < 1:
            if label == -1:
                continue

            eeg_path = os.path.join(
                data_dir, pid, "eeg", f"{pid}_task-eyesclosed_eeg.set"
            )
#            if not os.path.exists(eeg_path):
#                continue

            if not os.path.exists(eeg_path):
                print(f"❌ EEG manquant : {eeg_path} pour patient {pid} — label = {label}")
                continue
            else:
                print(f"✅ EEG trouvé pour {pid} — label = {label}")


            try:
                # Lecture via MNE
                raw = mne.io.read_raw_eeglab(eeg_path, preload=True, verbose=False)
                raw.filter(0.5, 45)
                raw.resample(fs)

                # Récupération des 19 premiers canaux (si la config standard le permet)
                data = raw.get_data(picks=raw.ch_names[:num_electrodes], units="uV").T

                # On segmente par blocs de 512 échantillons
                nb_segments = data.shape[0] // samples
                for i in range(nb_segments):
                    seg = data[i*samples:(i+1)*samples]  # (512, 19)

                    try:
                        # On calcule les features
                        feat = extract_features(seg)
                        if feat.shape[0] != FEATURE_SIZE:
                            print(f"⚠️ Segment ignoré (shape features invalide): {feat.shape}")
                            continue

                        # Concatène : données brutes + features
                        raw_flat = seg.flatten()  # 512*19 = 9728
                        combined = np.concatenate([raw_flat, feat])  # total ~9995

                        # On stocke dans le HDF5
                        f["X"].resize(offset+1, axis=0)
                        f["y"].resize(offset+1, axis=0)

                        f["X"][offset] = combined
                        f["y"][offset] = label

                        f["subj"].resize(offset + 1, axis=0)
                        f["subj"][offset] = pid  # <- ex: "sub-003"

                        offset += 1

                    except Exception as e:
                        print(f"❌ Extraction échouée (segment {i}) - {e}")

            except Exception as e:
                print(f"❌ Fichier {pid} ignoré - {e}")


# ====================================================================================
# === DATASET PYTORCH
# ====================================================================================
class EEGHybridDataset(Dataset):
    """
    Dataset PyTorch qui lit depuis le HDF5 :
    - la partie brute (512*19 points) pour construire les patches
    - la partie "features" (env. 267 points)
    """
    def __init__(self, h5_path, patch_len=64, augment=True):
        super().__init__()
        self.h5 = h5py.File(h5_path, 'r')
        self.X = self.h5["X"][:]
        self.y = self.h5["y"][:]
        self.augment = augment

        self.patch_len = patch_len
        self.num_patches = samples // patch_len  # 512 / 64 = 8
        self.channels = num_electrodes

        # On standardise l'ensemble du vecteur (raw + features) pour le SVM + partie MLP
        self.scaler = StandardScaler().fit(self.X)

    def __len__(self):
        return len(self.X)

    def __getitem__(self, idx):
        full_feat = self.X[idx]  # shape : ~9995
        label = int(self.y[idx])

        # Sépare la partie brute et la partie features
        raw_part = full_feat[:RAW_SIZE]          # 9728
        feat_part = full_feat[RAW_SIZE:]         # ~267

        # On restaure la forme (512, 19)
        eeg = raw_part.reshape(samples, self.channels)

        # Normalisation par canal
        eeg = (eeg - eeg.mean(axis=0)) / (eeg.std(axis=0) + 1e-6)

        # Quelques augmentations simples
        if self.augment:
            # Inversion temporelle (prob 0.2)
            if np.random.rand() < 0.2:
                eeg = eeg[::-1]
            # Bruit gaussien (prob 0.2)
            if np.random.rand() < 0.2:
                eeg += np.random.normal(0, 0.3, eeg.shape)

        # Construction des patches (8 patches de 64 échantillons, chacun de 19 canaux)
        patch = eeg.reshape(self.num_patches, self.patch_len, self.channels)
        patch = patch.transpose(0, 2, 1).reshape(self.num_patches, -1)  # (8, 1216)

        # Tensor pour la partie patch
        patch = torch.tensor(patch, dtype=torch.float32)

        # On scale la totalité du vecteur
        scaled_full = self.scaler.transform([full_feat])[0]  # -> shape ~ (9995,)

        # Pour la partie MLP, on n'a besoin que des ~267 dernières
        scaled_features = scaled_full[RAW_SIZE:]  # shape ~ (267,)

        feat = torch.tensor(scaled_features, dtype=torch.float32)
        y = torch.tensor(label, dtype=torch.long)

        return patch, feat, y


# ====================================================================================
# === MODÈLE
# ====================================================================================
#class ADFormerHybrid(nn.Module):
#    def __init__(self,
#                 patch_dim=64*19,      # 1216
#                 num_patches=8,        # 512/64
#                 feature_dim=MODEL_FEATURE_DIM,  # 267
#                 d_model=256,
#                 num_classes=2):
#        super().__init__()

        # Embed linéaire des patches
#        self.embed_patch = nn.Linear(patch_dim, d_model)

        # Positionnel (simple)
#        self.pos_embed = nn.Parameter(torch.randn(1, num_patches, d_model))

        # Transformer
#        encoder_layer = nn.TransformerEncoderLayer(d_model=d_model, nhead=4, batch_first=True)
#        self.transformer = nn.TransformerEncoder(encoder_layer, num_layers=4)

        # Encodeur MLP pour la partie features
#        self.feature_encoder = nn.Sequential(
#            nn.LayerNorm(feature_dim),
#            nn.Linear(feature_dim, d_model),
#            nn.ReLU(),
#            nn.Dropout(0.2),
#            nn.Linear(d_model, d_model)
#        )

        # Tête de classification fusionnée
#        self.head = nn.Sequential(
#            nn.LayerNorm(d_model * 2),
#            nn.Linear(d_model * 2, d_model),
#            nn.ReLU(),
#            nn.Dropout(0.1),
#            nn.Linear(d_model, num_classes)
#        )

#    def forward(self, patches, features):
        # Encode les patches via Transformer
#        p = self.embed_patch(patches) + self.pos_embed
#        p = self.transformer(p)  # shape (batch_size, 8, d_model)
#        p = p[:, -1]             # On récupère le dernier patch encodé

        # Encode les features
#        f = self.feature_encoder(features)

        # Fusion
#        x = torch.cat([p, f], dim=-1)  # (batch_size, d_model*2)
#        return self.head(x)           # (batch_size, num_classes)


class ADFormerHybrid(nn.Module):
    """
    Version améliorée du modèle hybride EEG :
    - Mean pooling sur les patches (au lieu de prendre le dernier)
    - Injection directe des features dans les tokens (token fusion)
    - MLP sur features en parallèle
    - Fusion finale avant classification
    """
    def __init__(self,
                 patch_dim=64*19,      # 1216
                 num_patches=8,
                 feature_dim=267,
                 d_model=256,
                 num_classes=2):
        super().__init__()

        # Encode les patches
        self.embed_patch = nn.Linear(patch_dim, d_model)

        # Positional encoding
        self.pos_embed = nn.Parameter(torch.randn(1, num_patches, d_model))

        # Transformer Encoder
        encoder_layer = nn.TransformerEncoderLayer(d_model=d_model, nhead=4, batch_first=True)
        self.transformer = nn.TransformerEncoder(encoder_layer, num_layers=4)

        # MLP pour les features
        self.feature_encoder = nn.Sequential(
            nn.LayerNorm(feature_dim),
            nn.Linear(feature_dim, d_model),
            nn.ReLU(),
            nn.Dropout(0.2),
            nn.Linear(d_model, d_model)
        )

        # Classification
        self.head = nn.Sequential(
            nn.LayerNorm(d_model * 2),
            nn.Linear(d_model * 2, d_model),
            nn.ReLU(),
            nn.Dropout(0.1),
            nn.Linear(d_model, num_classes)
        )

    def forward(self, patches, features):
        """
        patches : (batch_size, 8, 1216)
        features : (batch_size, 267)
        """
        # Encode features une fois
        f = self.feature_encoder(features)  # shape (B, d_model)

        # Fusion token-level : broadcast des features sur chaque patch
        f_token = f.unsqueeze(1).expand(-1, patches.size(1), -1)  # shape (B, 8, d_model)

        # Encode les patches + ajout positionnel
        p = self.embed_patch(patches) + self.pos_embed  # shape (B, 8, d_model)

        # Injection des features dans chaque token
        p = p + f_token  # token fusion

        # Transformer
        p = self.transformer(p)  # shape (B, 8, d_model)

        # Mean pooling au lieu de prendre le dernier token
        p = p.mean(dim=1)  # shape (B, d_model)

        # Fusion finale
        x = torch.cat([p, f], dim=-1)  # shape (B, d_model*2)
        out = self.head(x)            # shape (B, num_classes)
        return out


# ====================================================================================
# === FONCTION D'ENSEMBLE PREDICT
# ====================================================================================

# Moyenne softmax (mode "soft")
def ensemble_predict(models, patch, feat):
    """
    Retourne la moyenne des probabilités de chaque modèle.
    Exemple d'usage :
        preds = ensemble_predict([model1, model2, model3], patch, feat)
        classe_predite = preds.argmax(dim=1)
    """
    preds = []
    for model in models:
        model.eval()
        with torch.no_grad():
            logits = model(patch, feat)
            preds.append(F.softmax(logits, dim=1))
    # On moyenne les distributions
    return torch.stack(preds).mean(dim=0)

# Vote majoritaire (mode "hard")
def ensemble_vote_majoritaire(models, patch, feat):
    votes = []
    for model in models:
        model.eval()
        with torch.no_grad():
            logits = model(patch, feat)
            pred = torch.argmax(logits, dim=1).item()
            votes.append(pred)
    return Counter(votes).most_common(1)[0][0]

# ====================================================================================
# === FONCTION D'ENTRAÎNEMENT (LOS0)
# ====================================================================================
#def train_loso(seed, save_path, h5_file):
    """
    Entraîne le modèle ADFormerHybrid (et un SVM si plusieurs classes).
    Paramètres:
        seed (int)      : seed pour la reproductibilité
        save_path (str) : chemin de sauvegarde du modèle
        h5_file (str)   : chemin du dataset HDF5
    """
#    set_seed(seed)

#    dataset = EEGHybridDataset(h5_file)
#    class_counts = Counter(dataset.y)
#    print(f"Seed: {seed}")
#    print(f"📊 Répartition des classes : {class_counts}")

#    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
#    print("Utilisation de :", device)

    # Modèle ADFormer
#    model = ADFormerHybrid(num_classes=2).to(device)

    # Vérif du nombre de classes (pour le SVM)
#    svm = None
#    if len(class_counts) < 2:
#        print(f"⚠️ Pas assez de classes ({class_counts}) pour l'entraînement SVM. SVM ignoré.")
#    else:
        # Entraînement du SVM sur la totalité du vecteur
#        print("Entraînement du SVM (peut être long selon la taille du dataset)...")
#        svm = SVC(probability=True, kernel='rbf')
#        svm.fit(dataset.X, dataset.y)

#    loader = DataLoader(dataset, batch_size=32, shuffle=True)
#    opt = AdamW(model.parameters(), lr=2e-4)
#    loss_fn = nn.CrossEntropyLoss()

    # Entraînement simple sur 30 époques
#    for epoch in range(1, 31):
#        model.train()
#        correct = 0
#        total_loss = 0.0

#        for patch, feat, y in tqdm(loader, desc=f"Epoch {epoch}"):
#            patch, feat, y = patch.to(device), feat.to(device), y.to(device)

            # Sortie du modèle
#            logits = model(patch, feat)

            # Fusion SVM + Réseau si SVM existe
#            if svm is not None:
#                with torch.no_grad():
                    # On recompose le vecteur complet pour le SVM
                    # (patch brut + feat), puis on applique le scaler
                    # correspondant au dataset. (Ici, le code illustre
                    # une logique de fusion ; en pratique on peut
                    # entraîner le SVM sur la partie features uniquement.)
                    # On simplifie pour la démonstration.
#                    batch_rebuilt = []
#                    for i_batch in range(len(patch)):
                        # patch[i_batch] : shape (8, 1216)
                        # on "déplie" (8*1216) = 9728 et on concat feat[i_batch] ~267
#                        raw_part = patch[i_batch].view(-1).cpu().numpy()
#                        full_vec = np.concatenate([raw_part, feat[i_batch].cpu().numpy()])
#                        batch_rebuilt.append(full_vec)
                    # Applique le scaler SVM
#                    batch_rebuilt_scaled = dataset.scaler.transform(batch_rebuilt)
#                    svm_probs = torch.tensor(
#                        svm.predict_proba(batch_rebuilt_scaled),
#                        device=device,
#                        dtype=torch.float32
#                    )
#                fusion = (F.softmax(logits, dim=1) + svm_probs) / 2.0
#            else:
#                fusion = F.softmax(logits, dim=1)

#            loss = loss_fn(torch.log(fusion), y)

#            opt.zero_grad()
#            loss.backward()
#            opt.step()

#            total_loss += loss.item()
#            correct += (fusion.argmax(dim=1) == y).sum().item()

#        acc = correct / len(dataset)
#        print(f"\n✅ Epoch {epoch} | Loss: {total_loss:.4f} | Acc: {acc*100:.2f}%")

    # Sauvegarde du modèle
#    torch.save(model.state_dict(), save_path)
#    print(f"\n🎯 Modèle enregistré sous {save_path}")


def train_loso(seed, save_path, h5_file):
    """
    Entraîne le modèle ADFormerHybrid (et un SVM si binaire) avec split train/val.
    """
    set_seed(seed)

    dataset = EEGHybridDataset(h5_file)
    class_counts = Counter(dataset.y)
    print(f"Seed: {seed}")
    print(f"📊 Répartition des classes : {class_counts}")

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print("Utilisation de :", device)

    # Split train / val
    indices = np.arange(len(dataset))
    train_idx, val_idx = train_test_split(indices, test_size=0.2, stratify=dataset.y)
    train_set = Subset(dataset, train_idx)
    val_set = Subset(dataset, val_idx)

    train_loader = DataLoader(train_set, batch_size=32, shuffle=True)
    val_loader = DataLoader(val_set, batch_size=32, shuffle=False)

    # Modèle
    model = ADFormerHybrid(num_classes=2).to(device)

    # SVM (optionnel)
    svm = None
    if len(class_counts) < 2:
        print(f"⚠️ Pas assez de classes ({class_counts}) pour le SVM. Ignoré.")
    else:
        print("Entraînement du SVM...")
        svm = SVC(probability=True, kernel='rbf')
        svm.fit(dataset.X[train_idx], dataset.y[train_idx])

    opt = AdamW(model.parameters(), lr=2e-4)
    loss_fn = nn.CrossEntropyLoss()
    eps = 1e-8  # pour sécurité du log

    best_val_acc = 0

    for epoch in range(1, 31):
        model.train()
        total_loss = 0
        correct = 0

        for patch, feat, y in tqdm(train_loader, desc=f"Epoch {epoch}"):
            patch, feat, y = patch.to(device), feat.to(device), y.to(device)

            logits = model(patch, feat)

            if svm is not None:
                batch_rebuilt = []
                for i_batch in range(len(patch)):
                    raw_part = patch[i_batch].view(-1).cpu().numpy()
                    full_vec = np.concatenate([raw_part, feat[i_batch].cpu().numpy()])
                    batch_rebuilt.append(full_vec)
                batch_scaled = dataset.scaler.transform(batch_rebuilt)
                svm_probs = torch.tensor(svm.predict_proba(batch_scaled), device=device, dtype=torch.float32)
                fusion = (F.softmax(logits, dim=1) + svm_probs) / 2.0
            else:
                fusion = F.softmax(logits, dim=1)

#           loss = loss_fn(torch.log(fusion), y)
            loss = F.cross_entropy(logits, y)

            opt.zero_grad()
            loss.backward()
            opt.step()


            # Pour le suivi de l'acc
            preds = logits.argmax(dim=1)
            correct += (preds == y).sum().item()
            total_loss += loss.item()

#            total_loss += loss.item()
#            correct += (fusion.argmax(dim=1) == y).sum().item()

        train_acc = correct / len(train_set)
        print(f"\n✅ Epoch {epoch} | Train Loss: {total_loss:.4f} | Train Acc: {train_acc*100:.2f}%")

        # === VALIDATION
        model.eval()
        val_correct = 0
        val_total = 0
        with torch.no_grad():
            for patch, feat, y in val_loader:
                patch, feat, y = patch.to(device), feat.to(device), y.to(device)
                logits = model(patch, feat)
                preds = logits.argmax(dim=1)
                val_correct += (preds == y).sum().item()
                val_total += len(y)

        val_acc = val_correct / val_total
        print(f"🧪 Validation Accuracy : {val_acc*100:.2f}%")

        if val_acc > best_val_acc:
            best_val_acc = val_acc
            # Sauvegarde du modèl complet .pth
            torch.save(model, save_path)
            print(f"💾 Nouveau meilleur modèle sauvegardé (Val Acc: {val_acc*100:.2f}%)")
            # Génère nom du scaler .pkl basé sur le .pth
            scaler_name = os.path.splitext(save_path)[0] + "_scaler.pkl"
            joblib.dump(dataset.scaler, scaler_name)
            print(f"💾 Nouveau meilleur Scaler sauvegardé : {scaler_name}")


    print(f"\n🎯 Entraînement terminé. Meilleur modèle sauvegardé sous : {save_path}")


# ====================================================================================
# === MAIN
# ====================================================================================
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Entraînement ADFormer-Hybrid (LOS0).")
    parser.add_argument('--seed', type=int, default=42, help='Seed pour la reproductibilité')
    parser.add_argument('--save', type=str, default='adformer_depistage_model_loss_scaler.pth',
                        help='Chemin de sauvegarde du modèle entraîné')
    args = parser.parse_args()

    # Dossier où se trouvent les données BIDS
    data_dir = "/workspace/memory_os_ai/alz/"
    h5_file = os.path.join(data_dir, "eeg_data_alzheimer_depistage_loss_scaler.h5")

    # Construction du HDF5 (si non déjà fait)
    if not os.path.exists(h5_file):
        build_h5(data_dir, h5_file)

    # Entraînement (LOS0)
    train_loso(args.seed, args.save, h5_file)
