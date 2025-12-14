## Izypower Titan — Intégration Home Assistant

Cette intégration permet à Home Assistant de dialoguer localement avec un ou plusieurs appareils Izypower Titan, afin de récupérer leurs données.

Elle est basée sur l’intégration Indevolt et sur le travail de Speedy2524, disponible ici :
https://github.com/Speedy2524/homeassistant-indevolt

Une partie du code, des concepts et de la structure provient de ce projet, qui a permis la création de cette adaptation pour les appareils Titan Izypower.

## ✨ Fonctionnalités

Communication entièrement en local (aucun cloud requis)

Détection automatique du Titan et récupération du numéro de série

Accès aux données internes (production, batterie, puissance AC/DC…)

Capteur d’état de connectivité (OK / KO)

Possibilité d’enregistrer plusieurs Titans


## 🧱 Structure de l’intégration

Composants principaux :
- gestion de configuration et options
config_flow

- définition des IDs et métadonnées capteurs
const

- coordinateur de mise à jour
coordinator

- API d’échange avec l’appareil
izypower_api

- création des entités Home Assistant
sensor

- déclaration générale de l’intégration
manifest

Les valeurs brutes renvoyées par le Titan sont normalisées et converties en entités cohérentes dans Home Assistant (unités, classes, mapping enum…), grâce notamment à :
-utils

## 🔧 Installation
Attention: il faudra utiliser l'application Energy Ease pour activer l'API local. MAIS en aucun cas l'utiliser pour le reste. ( vous pouvez même la désinstaller une fois le paramétre modifié)
Une fois que vous avez installé l'application et ajouté votre batterie vous serez en mesure d'activer l'API local. CF screen en dessous
<img width="1518" height="3128" alt="README_HACS_steps_1-4_grid" src="https://github.com/user-attachments/assets/ca03301d-4929-401a-99ca-75b690caad0f" />

Installation HACS
Comme pour les autres intégration communautaire ;)
Copier coller le lien du git: https://github.com/khirale/izypower_titan.git

Installation manuelle
Copier le dossier izypower_titan dans :
/config/custom_components/

Puis redémarrer Home Assistant.

Enfin, dans Home Assistant :
Paramètres → Appareils & Services → Ajouter une intégration → Izypower Titan

## ⚙️ Configuration
Informations nécessaires :
IP du Titan
Port (par défaut 8080)
Intervalle de rafraîchissement

La connexion initiale vérifie l’accessibilité du module via :
config_flow

## 📡 Fiabilité & tolérance aux erreurs

Le coordinateur :
- interroge le Titan à intervalle régulier
- mémorise les valeurs connues si aucune donnée ne revient
- gère et journalise les erreurs éventuelles
- indique l’état de connectivité via un capteur dédié

Fonctionnement détaillé :
coordinator

## 🔒 Fonctionnement local
aucune requête externe
aucun cloud utilisé
aucune transmission vers Izypower
aucune dépendance vers un service Internet

Déclaré en local_polling dans le manifest :
manifest

## 🙏 Remerciements & crédit

Cette intégration est rendue possible grâce :
à la collaboration de Charmg31, Wellgo et le soutien de MaterFrance
