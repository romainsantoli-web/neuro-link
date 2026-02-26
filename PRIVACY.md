# Politique de Confidentialité — Neuro-Link

*Dernière mise à jour : 26 février 2026*

## 1. Responsable du traitement

**Kocupyr Romain**
Email : romain.kocupyr@neuro-link.ai

## 2. Données collectées

### 2.1 Données EEG
- Les fichiers EEG téléchargés sont traités **exclusivement en temps réel** pour
  l'analyse IA.
- Les fichiers sont **supprimés automatiquement** après traitement (stockage
  temporaire uniquement pendant l'inférence).
- Aucun fichier EEG n'est conservé, partagé, ou transmis à des tiers.

### 2.2 Données de session
- **Identifiant de session** : UUID anonyme généré côté client.
- **Résultats d'analyse** : statut (AD/CN), stade, confiance, rapport — stockés
  dans un fichier local JSONL.
- **Aucune donnée nominative** n'est collectée (pas de nom, email, adresse IP
  persistante).

### 2.3 Données de navigation (landing page)
- Aucun cookie de tracking.
- Aucun outil d'analytics tiers (pas de Google Analytics, Meta Pixel, etc.).
- Les liens sponsorisés sont statiques et ne collectent aucune donnée.

## 3. Base légale du traitement (Art. 6 RGPD)

- **Consentement** (Art. 6.1.a) : L'utilisateur consent au traitement en
  téléchargeant volontairement un fichier EEG.
- **Intérêt légitime** (Art. 6.1.f) : Sécurité du service (rate limiting,
  détection d'intrusion).

## 4. Durée de conservation

| Donnée | Durée | Justification |
|--------|-------|---------------|
| Fichier EEG uploadé | Durée de l'inférence (~10s) | Supprimé automatiquement |
| Résultats d'analyse | 90 jours | Contexte mémoire session |
| Logs serveur | 30 jours | Sécurité et debugging |
| Compteurs rate-limit | En mémoire uniquement | Jamais persisté sur disque |

## 5. Vos droits (Art. 15-22 RGPD)

Vous disposez des droits suivants :

- **Accès** : Demander une copie de vos données.
- **Rectification** : Corriger des données inexactes.
- **Effacement** ("droit à l'oubli") : Supprimer vos données.
- **Portabilité** : Recevoir vos données dans un format structuré.
- **Opposition** : Vous opposer au traitement.
- **Limitation** : Restreindre le traitement.

Pour exercer vos droits : **romain.kocupyr@neuro-link.ai**

Délai de réponse : 30 jours maximum.

## 6. Sécurité des données

- Chiffrement TLS 1.2/1.3 en transit (HTTPS obligatoire).
- Rate limiting et blocage automatique des IP suspectes.
- Validation des entrées (anti-injection SQL, XSS, path traversal).
- Authentification par token Bearer en mode strict.
- Sandboxing du processus serveur (systemd : NoNewPrivileges, ProtectSystem).
- Aucune base de données externe — stockage local JSONL uniquement.

## 7. Transferts internationaux

Aucun transfert de données hors de l'Union Européenne.
Le service est hébergé sur un serveur situé dans l'UE.

## 8. Sous-traitants

Aucun sous-traitant n'a accès aux données EEG ou aux résultats d'analyse.

## 9. Avertissement médical

Neuro-Link est un **outil de recherche** et ne constitue pas un dispositif
médical certifié (CE/FDA). Les résultats ne doivent pas être utilisés comme
base unique de décision médicale. Consultez un professionnel de santé qualifié.

## 10. Modifications

Cette politique peut être mise à jour. La date de dernière modification est
indiquée en haut du document. Les utilisateurs seront informés des changements
significatifs via l'interface de l'application.

## 11. Contact DPO

Pour toute question relative à la protection des données :
**romain.kocupyr@neuro-link.ai**

## 12. Réclamation

Vous pouvez introduire une réclamation auprès de la CNIL :
https://www.cnil.fr/fr/plaintes
