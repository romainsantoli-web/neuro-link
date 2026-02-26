#!/bin/bash

# === CONFIGURATION ===
H5_PATH="/workspace/memory_os_ai/alz/eeg_data_alzheimer_99_id_C.h5"
OUTDIR="/workspace/memory_os_ai/ad_id_99_c_scaler/rapport"

echo "🚀 Lancement de l'analyse complète EEG NeuroFormer"
echo "📂 Dataset : $H5_PATH"
echo "📁 Dossier de sortie : $OUTDIR"
echo "---------------------------------------------"

# === 1. Prédictions + XAI
echo "🔎 Étape 1 : Prédictions patient + XAI"
python evalutate_99_seg_all.py.py --mode both

# === 2. Graphe de connectivité par groupe
echo "🔗 Étape 2 : Génération des graphes connectivité EEG"
python generate_connectivity_visualization_AD_severity.py --h5 "$H5_PATH" --group Léger
python generate_connectivity_visualization_AD_severity.py --h5 "$H5_PATH" --group Modéré
python generate_connectivity_visualization_AD_severity.py --h5 "$H5_PATH" --group Sévère

# === 3. Comparaison connectivité AD vs CN
echo "📊 Étape 3 : Comparaison connectivité AD vs CN"
python connectivity_comparison_AD_severity_99_id.py --h5 "$H5_PATH"

# === 4. Analyse PSD (spectre EEG)
echo "📈 Étape 4 : Analyse spectrale PSD (tous les groupes)"
GROUPS=("Léger" "Modéré" "Sévère" "AD" "Tous")

for group in "${GROUPS[@]}"
do
  echo "   ➤ Groupe $group"
  python generate_psd_comparison_AD_severity_99_id.py --h5 "$H5_PATH" --group "$group" --outdir "$OUTDIR"
done

echo "✅ Analyse complète terminée avec succès."
