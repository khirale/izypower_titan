[![HACS Custom](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://hacs.xyz)
[![Version](https://img.shields.io/badge/version-2.0-brightgreen)]

## ⚡ Izypower Titan – Intégration Home Assistant

Intégration Home Assistant permettant le suivi complet et le pilotage avancé des batteries Izypower Titan, en local (MR1) ou via le Cloud (Smart IA).

<p align="center">
  <a href="https://buymeacoffee.com/khirale">
    <img
      src="https://cdn.buymeacoffee.com/buttons/v2/default-yellow.png"
      alt="Buy Me a Coffee"
      height="45"
    >
  </a>
</p>


## 🚧 Installation:
![Status](https://img.shields.io/badge/status-warning-orange)
**ATTENTION**, il s'agit d'une nouvelle intégration donc si vous aviez déja l'intégration de configurer dans votre Home Assistant vous devez:
- **Supprimer les Titans déja intégrées**
- **Redémarrer Home Assistant**
- Mettre à jour l'intégration via HACS
- Redémarrer Home Assistant
- Réintégrer les titans avec le nouveau formulaire

Pour tous les nouveaux utilisateurs, il s'agit d'une installation classique via HACS:
- Ajout du dépots
- Télécharger
- Redémarrer Home Assistant
- Configurer l'intégration

## 🧩 Que permet cette intégration ?
📊 **Supervision complète**

L’intégration expose automatiquement :

- Production photovoltaïque (PV1 à PV4)
- Puissance AC entrée / sortie
- Énergie cumulée importée / exportée
- État et puissance batterie
- SOC batterie (%)
- Températures batterie
- Mode de fonctionnement (Standby, Self-consumed, Intelligent, etc.)
- Statut de connectivité locale
- Statut Cloud
- Découverte automatique des batteries LINK
- etc.

👉 Toutes les données sont locales, avec restauration d’état après redémarrage.


🎛️ **Pilotage de la batterie**
<img width="1536" height="1024" alt="visuel" src="https://github.com/user-attachments/assets/c90f5054-91ab-4039-a0cf-3a017fe9a921" />



Deux modes de pilotage sont disponibles selon le Smart Meter que vous utilisez :

| Meter	| Mode	| Communication |
|-----------|-----------|-----------|
| MR1	| Local	| Directement avec la Titan (LAN) |
| Smart IA	| Cloud	| Via l’API officielle Izypower |

Listes de commandes disponibles par type de meter:
| Commande                                     | Smart&nbsp;IA | MR1 | Paramètres                                                                                                                     |
| -------------------------------------------- | :--------: | :---: | ------------------------------------------------------------------------------------------------------------------------------ |
| **Charge**                                   | ✅        | ✅   | Demande à la batterie de se charger en fonction de la puissance de charge et **SOC limite de charge** (% de batterie à partir duquel la charge s’arrête automatiquement, ex. : 95 %) |
| **Décharge**                                 | ❌        | ✅   | Demande à la batterie de se décharger en fonction de la puissance de décharge. La batterie s’arrête automatiquement lorsque le **SOC de sécurité** est atteint                         |
| **Standby**                                  | ✅        | ✅   | Met la batterie en état de veille                                                                                              |
| **Mode&nbsp;intelligent**                         | ✅        | ❌   | Bascule la batterie en mode *Intelligent*                                                                                      |
| **Mode&nbsp;self-consumed**                       | ❌        | ✅   | Bascule la batterie en mode *Self-consumed* (autoconsommation)                                                                 |
| **Mode&nbsp;Real-Time**                           | ❌        | ✅   | Permet à la batterie d’accepter les commandes locales — **obligatoire pour les utilisateurs MR1**                              |
| **Mode&nbsp;manuel**                              | ✅        | ✅   | Bascule la batterie en mode manuel <br>*(pour Smart IA, ce mode est inclus dans les commandes Charge et Standby)*              |
| **Puissance&nbsp;de&nbsp;charge<br>(mode manuel)**        | ✅        | ✅   | Modifie la puissance de charge en mode manuel                                                                                  |
| **SOC&nbsp;de&nbsp;charge&nbsp;max<br>(mode manuel)**          | ✅        | ✅   | Modifie le SOC maximum de charge en mode manuel                                                                                |
| **Puissance&nbsp;de&nbsp;décharge<br>(mode manuel)**      | ❌        | ✅   | Modifie la puissance de décharge en mode manuel                                                                                |
| **Puissance&nbsp;de&nbsp;charge<br>(mode intelligent)**   | ✅        | ❌   | Modifie la puissance de charge en mode Intelligent                                                                             |
| **Puissance&nbsp;de&nbsp;décharge<br>(mode intelligent)** | ✅        | ❌   | Modifie la puissance de décharge en mode Intelligent                                                                           |


## 🔧 Fonctionnement du pilotage
**Pour le MR1 :**
Il est obligatoire de basculer la Titan en mode Real-Time
(via le bouton physique ou le service associé).

⚠️ **Cas des installations en cluster**

Les Titans slaves ne passent pas visuellement en mode Real-Time.
Elles restent affichées en mode Self-consumed (autoconsommation), mais restent entièrement pilotées par la Titan master.

➡️ Il s’agit d’un problème uniquement visuel, sans impact fonctionnel.
Une correction est prévue dans une version future.

| Paramètre	| Type	| Description |
|-----------|-----------|-----------|
| Charge / Discharge Power	| Slider	| Puissance cible (W) |
| Charge SOC Max	| Slider	| SOC maximum autorisé (%) |

## 🔁 Exemple de pilotage – Mode MR1 (Local)
🚧 **Toujours utiliser le Real-Time mode** avant de lancer des commandes sur les Titans (Disponible via le bouton)

Forcer une charge locale contrôlée.

**Étapes**

1️⃣ **Régler les paramètres**

**Charge / Discharge Power** → 800 W à 7200 W (selon votre configuration)

**Charge SOC Max** → 100 %
(plage 0–100 % : la charge s’arrête automatiquement lorsque le SOC atteint cette valeur)

2️⃣ Utiliser les boutons

**MR1 Real-Time mode**

**MR1 Start Charge**

➡️ Fonctionne même sans Internet.

## 🔁 Exemple de pilotage – Mode Smart IA (Cloud)
Forcer une charge intelligente via le Cloud Izypower.

**Étapes**

1️⃣ **Régler le slider**

**Charge / Discharge Power** → 800 W à 7200 W (selon votre configuration)

**Charge SOC Max** → 100 %
(plage 0–100 % : la charge s’arrête automatiquement lorsque le SOC atteint cette valeur)

2️⃣ **Appuyer sur**

**Smart IA – Start Charge**

➡️ Fonctionne uniquement via le Cloud Izypower.

## 🙏 Remerciements & crédit
Cette intégration est rendue possible grâce à la collaboration de Charmg31 et Wellgo.
