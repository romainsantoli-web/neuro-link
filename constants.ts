export const MOCK_REPORT_TEMPLATE = `
**COMPTE RENDU CLINIQUE NEURO-LINK**

**Patient ID :** PAT-8X92-LZ
**Date :** {{DATE}}
**Heure d'inférence :** {{TIME}}

---

### Diagnostic et Confiance
* **Statut Final :** {{STATUS}}
* **Stade Estimé :** {{STAGE}}
* **Confiance Modèle :** {{CONFIDENCE}}%

---

### Interprétation des Graphiques et Justification IA
L'analyse spectrale révèle une diminution significative de la puissance dans la bande Alpha (8-13 Hz) couplée à une augmentation de l'activité Thêta (4-8 Hz) dans les régions temporo-pariétales. L'entropie de permutation suggère une dysconnexion fonctionnelle caractéristique.

[IMAGE_XAI]

### Conclusion Clinique
Le profil neurophysiologique est fortement corrélé avec les biomarqueurs EEG d'un déclin cognitif de type Alzheimer. Il est recommandé de procéder à une IRM structurelle pour confirmer l'atrophie hippocampique potentielle.

### Vérification de la Traçabilité
Le hash cryptographique des données EEG brutes correspond à l'entrée enregistrée dans la blockchain médicale privée. Aucune altération du signal détectée durant le pipeline de pré-traitement.

[IMAGE_QR]
`;

export const IDLE_WAVE_DATA = Array.from({ length: 50 }, (_, i) => ({
  name: i.toString(),
  alpha: Math.sin(i * 0.2) * 20 + 50,
  theta: Math.cos(i * 0.15) * 15 + 40,
}));