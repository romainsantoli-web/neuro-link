#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import math
from collections import Counter

import antropy as ant
import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F
from pykalman import KalmanFilter
from scipy.signal import welch
from scipy.stats import iqr

fs = 128
samples = 512
num_electrodes = 19
patch_len = 64
num_patches = samples // patch_len

RAW_SIZE = samples * num_electrodes
FEATURE_SIZE = 267
TOTAL_FEATURE_SIZE = RAW_SIZE + FEATURE_SIZE
MODEL_FEATURE_DIM = FEATURE_SIZE

asym_pairs = [(3, 5), (13, 15), (0, 1)]
bands = {
    'Delta': (0.5, 4),
    'Theta': (4, 8),
    'Alpha1': (8, 10),
    'Alpha2': (10, 13),
    'Beta1': (13, 20),
    'Beta2': (20, 30),
    'Gamma': (30, 45),
}

kf_model = KalmanFilter(initial_state_mean=0, n_dim_obs=1)


def kalman_filter_signal(signal):
    filtered, _ = kf_model.filter(signal[:, None])
    return filtered[:, 0]


def extract_features(data):
    if data.shape != (samples, num_electrodes):
        raise ValueError(f'Segment shape invalide : {data.shape}')

    mean_t = np.mean(data, axis=0)
    var_t = np.var(data, axis=0)
    iqr_t = iqr(data, axis=0)

    freqs, psd = welch(data, fs=fs, nperseg=samples, axis=0)
    band_feats = []
    kalman_means = []
    kalman_diffs = []

    for fmin, fmax in bands.values():
        idx = (freqs >= fmin) & (freqs <= fmax)
        raw_power = np.mean(psd[idx], axis=0)
        kalman_power = kalman_filter_signal(psd[idx].mean(axis=1))
        band_feats.append(raw_power)
        kalman_means.append(np.mean(kalman_power))
        kalman_diffs.append(raw_power.mean() - np.mean(kalman_power))

    rbp = np.stack(band_feats, axis=0)
    perm_en = np.array([ant.perm_entropy(data[:, i], order=3, normalize=True) for i in range(num_electrodes)])
    sample_en = np.array([ant.sample_entropy(data[:, i], order=2) for i in range(num_electrodes)])

    corr_matrix = np.corrcoef(data.T)
    clustering = np.array([
        np.sum(corr_matrix[i] > 0.5) / (num_electrodes - 1)
        for i in range(num_electrodes)
    ])
    path_length = np.mean(np.abs(corr_matrix))
    non_zero_corr = corr_matrix[np.abs(corr_matrix) > 0]
    efficiency = np.mean(1 / np.abs(non_zero_corr)) if len(non_zero_corr) > 0 else 0.0
    small_worldness = np.mean(clustering) / path_length if path_length != 0 else 0.0

    asym = np.array([np.mean(data[:, i] - data[:, j]) for i, j in asym_pairs])

    features = np.concatenate([
        mean_t,
        var_t,
        iqr_t,
        rbp.flatten(),
        perm_en,
        sample_en,
        clustering,
        asym,
        [path_length, efficiency, small_worldness],
        kalman_means,
        kalman_diffs,
    ])
    return features


class ADFormerHybrid(nn.Module):
    def __init__(
        self,
        patch_dim=64 * 19,
        num_patches=8,
        feature_dim=MODEL_FEATURE_DIM,
        d_model=256,
        num_classes=3,
    ):
        super().__init__()
        self.embed_patch = nn.Linear(patch_dim, d_model)
        self.pos_embed = nn.Parameter(torch.randn(1, num_patches, d_model))

        encoder_layer = nn.TransformerEncoderLayer(d_model=d_model, nhead=4, batch_first=True)
        self.transformer = nn.TransformerEncoder(encoder_layer, num_layers=4)

        self.feature_encoder = nn.Sequential(
            nn.LayerNorm(feature_dim),
            nn.Linear(feature_dim, d_model),
            nn.ReLU(),
            nn.Dropout(0.2),
            nn.Linear(d_model, d_model),
        )

        self.head = nn.Sequential(
            nn.LayerNorm(d_model * 2),
            nn.Linear(d_model * 2, d_model),
            nn.ReLU(),
            nn.Dropout(0.1),
            nn.Linear(d_model, num_classes),
        )

    def forward(self, patches, features):
        f = self.feature_encoder(features)
        p = self.embed_patch(patches) + self.pos_embed
        f_token = f.unsqueeze(1).expand(-1, p.size(1), -1)
        p = p + f_token
        p = self.transformer(p)
        p = p.mean(dim=1)
        x = torch.cat([p, f], dim=-1)
        return self.head(x)


def ensemble_predict(models, patch, feat):
    preds = []
    for model in models:
        model.eval()
        with torch.no_grad():
            logits = model(patch, feat)
            preds.append(F.softmax(logits, dim=1))
    return torch.stack(preds).mean(dim=0)


def ensemble_vote_majoritaire(models, patch, feat):
    votes = []
    for model in models:
        model.eval()
        with torch.no_grad():
            logits = model(patch, feat)
            pred = torch.argmax(logits, dim=1).item()
            votes.append(pred)
    return Counter(votes).most_common(1)[0][0]
