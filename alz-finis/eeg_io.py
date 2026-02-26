import os
import re
from typing import List, Optional, Tuple

import mne
import numpy as np
from scipy.signal import butter, filtfilt, resample_poly

SUPPORTED_MNE_EXTENSIONS = {'.set', '.edf', '.bdf', '.vhdr', '.fif'}
SUPPORTED_OPENBCI_EXTENSIONS = {'.csv', '.txt'}


def _load_mne_data(file_path: str, target_fs: int, target_channels: int) -> np.ndarray:
    ext = os.path.splitext(file_path)[-1].lower()
    loaders = {
        '.set': mne.io.read_raw_eeglab,
        '.edf': mne.io.read_raw_edf,
        '.bdf': mne.io.read_raw_bdf,
        '.vhdr': mne.io.read_raw_brainvision,
        '.fif': mne.io.read_raw_fif,
    }

    raw = loaders[ext](file_path, preload=True)
    raw.filter(0.5, 45)
    raw.resample(target_fs)
    data = raw.get_data(picks=raw.ch_names[:target_channels], units='uV').T

    if data.shape[1] < target_channels:
        pad = np.zeros((data.shape[0], target_channels - data.shape[1]), dtype=np.float64)
        data = np.concatenate([data, pad], axis=1)
    elif data.shape[1] > target_channels:
        data = data[:, :target_channels]

    return data

def _parse_openbci_lines(file_path: str) -> Tuple[Optional[List[str]], np.ndarray]:
    with open(file_path, 'r', encoding='utf-8', errors='ignore') as handle:
        raw_lines = [line.strip() for line in handle if line.strip()]

    lines = [line for line in raw_lines if not line.startswith('%') and not line.startswith('#')]
    if not lines:
        raise ValueError('Fichier OpenBCI vide ou sans lignes exploitables.')

    probe = '\n'.join(lines[:8])
    delimiter = ','
    if ',' not in probe and ';' not in probe and '\t' not in probe:
        delimiter = None
    else:
        try:
            import csv
            delimiter = csv.Sniffer().sniff(probe, delimiters=',;\t').delimiter
        except Exception:
            delimiter = ','

    header = None
    data_start = 0
    first_tokens = re.split(r'\s+' if delimiter is None else re.escape(delimiter), lines[0])

    is_header = False
    for token in first_tokens:
        token = token.strip().lower()
        if token and not re.fullmatch(r'[-+]?\d+(\.\d+)?', token):
            is_header = True
            break

    if is_header:
        header = [token.strip() for token in first_tokens]
        data_start = 1

    numeric_rows: List[List[float]] = []
    split_regex = r'\s+' if delimiter is None else re.escape(delimiter)

    for line in lines[data_start:]:
        tokens = [t.strip() for t in re.split(split_regex, line) if t.strip()]
        if not tokens:
            continue
        try:
            numeric_rows.append([float(token) for token in tokens])
        except ValueError:
            continue

    if not numeric_rows:
        raise ValueError('Impossible de parser des valeurs numériques OpenBCI.')

    min_len = min(len(row) for row in numeric_rows)
    numeric_rows = [row[:min_len] for row in numeric_rows]
    arr = np.asarray(numeric_rows, dtype=np.float64)

    if header is not None and len(header) > min_len:
        header = header[:min_len]

    return header, arr


def _find_sampling_rate_from_header(header: Optional[List[str]], arr: np.ndarray) -> Optional[float]:
    if not header:
        return None

    for idx, name in enumerate(header):
        low = name.lower()
        if 'timestamp' in low or low in {'time', 'ts'}:
            values = arr[:, idx]
            diffs = np.diff(values)
            diffs = diffs[np.isfinite(diffs) & (diffs > 0)]
            if len(diffs) == 0:
                continue
            dt = float(np.median(diffs))
            if dt > 1e3:
                return None
            if dt > 1:
                return 1000.0 / dt
            return 1.0 / dt
    return None


def _pick_openbci_channel_indices(header: Optional[List[str]], n_cols: int) -> List[int]:
    if header:
        selected = []
        for idx, name in enumerate(header):
            low = name.lower()
            if 'exg' in low or 'eeg' in low or re.match(r'^(ch|channel)\s*\d+', low):
                selected.append(idx)
        if selected:
            return selected

    if n_cols >= 9:
        return list(range(1, min(n_cols, 17)))
    return list(range(min(n_cols, 8)))


def _bandpass(data: np.ndarray, fs: int, low: float = 0.5, high: float = 45.0) -> np.ndarray:
    if data.shape[0] < 32:
        return data

    nyquist = fs / 2.0
    high_clamped = min(high, nyquist - 1e-3)
    if high_clamped <= low:
        return data

    b, a = butter(4, [low / nyquist, high_clamped / nyquist], btype='band')
    try:
        return filtfilt(b, a, data, axis=0)
    except ValueError:
        return data


def _normalize_channels(data: np.ndarray, target_channels: int) -> np.ndarray:
    if data.shape[1] > target_channels:
        return data[:, :target_channels]
    if data.shape[1] < target_channels:
        pad = np.zeros((data.shape[0], target_channels - data.shape[1]), dtype=np.float64)
        return np.concatenate([data, pad], axis=1)
    return data


def _normalize_units_uv(data: np.ndarray) -> np.ndarray:
    max_abs = float(np.nanmax(np.abs(data))) if data.size else 0.0
    if 0 < max_abs < 0.01:
        return data * 1e6
    return data


def _load_openbci_data(
    file_path: str,
    target_fs: int,
    target_channels: int,
    openbci_fs: Optional[float] = None,
) -> np.ndarray:
    header, arr = _parse_openbci_lines(file_path)
    channel_indices = _pick_openbci_channel_indices(header, arr.shape[1])
    if not channel_indices:
        raise ValueError('Aucune colonne canal OpenBCI détectée.')

    data = arr[:, channel_indices]
    data = _normalize_units_uv(data)

    source_fs = openbci_fs or _find_sampling_rate_from_header(header, arr) or 250.0

    if int(round(source_fs)) != target_fs:
        up = target_fs
        down = int(round(source_fs))
        data = resample_poly(data, up, down, axis=0)

    data = _bandpass(data, target_fs, low=0.5, high=45.0)
    data = _normalize_channels(data, target_channels)
    return data


def load_eeg_data(
    file_path: str,
    target_fs: int = 128,
    target_channels: int = 19,
    openbci_fs: Optional[float] = None,
) -> np.ndarray:
    ext = os.path.splitext(file_path)[-1].lower()

    if ext in SUPPORTED_MNE_EXTENSIONS:
        return _load_mne_data(file_path, target_fs=target_fs, target_channels=target_channels)

    if ext in SUPPORTED_OPENBCI_EXTENSIONS:
        return _load_openbci_data(
            file_path,
            target_fs=target_fs,
            target_channels=target_channels,
            openbci_fs=openbci_fs,
        )

    supported = sorted(SUPPORTED_MNE_EXTENSIONS | SUPPORTED_OPENBCI_EXTENSIONS)
    raise ValueError(f"❌ Format EEG non supporté : {ext}. Formats supportés: {', '.join(supported)}")
