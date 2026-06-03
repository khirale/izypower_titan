# Izypower Titan — Home Assistant Integration

[![Version](https://img.shields.io/badge/version-2.3.0-blue)](https://github.com/khirale/izypower_titan/releases)
[![HACS](https://img.shields.io/badge/HACS-Custom-orange)](https://hacs.xyz)
[![HA](https://img.shields.io/badge/Home%20Assistant-2026.1+-green)](https://www.home-assistant.io)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow)](LICENSE)


<p align="center">
  <a href="https://buymeacoffee.com/khirale">
    <img
      src="https://cdn.buymeacoffee.com/buttons/v2/default-yellow.png"
      alt="Buy Me a Coffee"
      height="45"
    >
  </a>
</p>


---

🇫🇷 [Français](#français) · 🇬🇧 [English](#english)

---

## Français

Intégration Home Assistant pour les batteries de stockage solaire **Izypower Titan**.  
Supporte le pilotage local (MR1) et cloud (Smart IA), les clusters multi-Titans, et les batteries Link.

### Table des matières

- [Fonctionnalités](#fonctionnalités)
- [Installation](#installation)
- [Configuration](#configuration)
- [Entités exposées](#entités-exposées)
- [Services](#services)
- [Cluster multi-Titans](#cluster-multi-titans)
- [Batteries Link](#batteries-link)
- [Calibration BMS](#calibration-bms)
- [Nouveautés v2.2.0](#nouveautés-v220)

---

### Fonctionnalités

- Supervision en temps réel de la production PV, des flux AC/DC, et de l'état de la batterie
- Contrôle local via RPC (mode MR1) ou cloud via l'API Izypower (mode Smart IA)
- Support des clusters jusqu'à 3 Titans (Master + Slaves) avec rollback automatique
- Découverte automatique des batteries Link connectées (toutes les heures)
- Validation intelligente des données énergie (protection contre les valeurs aberrantes)
- Restauration d'état après redémarrage HA

---

### Installation

#### Via HACS (recommandé)

1. Ouvrir HACS → **Intégrations** → menu ⋮ → **Dépôts personnalisés**
2. Ajouter `https://github.com/khirale/izypower_titan` · Catégorie : **Intégration**
3. Chercher **Izypower Titan** et cliquer **Télécharger**
4. Redémarrer Home Assistant
5. **Paramètres → Appareils et services → Ajouter une intégration** → rechercher *Izypower Titan*

Depuis la v2.2.0, la configuration peut être modifiée à tout moment **sans supprimer l'intégration** :

1. **Paramètres → Appareils et services**
2. Ouvrir la carte **Izypower Titan** → menu ⋮ → **Reconfigurer**
3. Tous les champs sont pré-remplis avec les valeurs courantes — modifier ce qui doit l'être
4. L'intégration se recharge automatiquement à la fin

Cas couverts :

| Scénario | Comportement |
|---|---|
| Ajouter un Titan (1→2, 2→3, 1→3) | Demande l'IP du/des nouveau(x) slave(s) |
| Retirer un Titan (3→2, 2→1, 3→1) | Les slaves retirés et leurs entités disparaissent |
| Changer l'IP d'un Titan existant | Pré-rempli avec l'ancienne IP |
| Basculer MR1 ↔ Smart IA | Demande / saute les credentials cloud |
| Activer/désactiver Override responsabilité | Respecte la nouvelle valeur |
| Modifier les credentials cloud | Username pré-rempli, mot de passe à ressaisir |

---

### Configuration

#### Mode de connexion

| Mode | Description | Prérequis |
|------|-------------|-----------|
| **MR1 (Local)** | Communication directe via RPC sur le réseau local | Titan accessible sur le LAN, port 8080 par défaut |
| **Smart IA (Cloud)** | Pilotage via l'API officielle Izypower | Compte Izypower + connexion internet |

#### Paramètres

| Paramètre | Description | Défaut |
|-----------|-------------|--------|
| Adresse IP | IP du Titan (ou Master si cluster) | — |
| Port | Port RPC local | `8080` |
| Nombre de Titans | 1 à 3 | `1` |
| Mode responsabilité | Standard (800 W/Titan) ou Override (2400 W/Titan) | Standard |
| Intervalle de poll | Fréquence de mise à jour en secondes | `5 s` |
| Identifiants cloud | Email + mot de passe (mode Smart IA uniquement) | — |

---

### Entités exposées

#### Capteurs — Production PV

| Entité | Registre | Unité | Description |
|--------|----------|-------|-------------|
| DC Input Power 1 | 1664 | W | Puissance PV 1 |
| DC Input Power 2 | 1665 | W | Puissance PV 2 |
| DC Input Power 3 | 1666 | W | Puissance PV 3 |
| DC Input Power 4 | 1667 | W | Puissance PV 4 |
| Total DC Output Power | 1501 | W | Puissance DC totale |

#### Capteurs — Flux AC

| Entité | Registre | Unité | Description |
|--------|----------|-------|-------------|
| AC Output Power | 2098 | W | Puissance AC en sortie |
| Total AC Output Power | 2108 | W | Puissance AC totale en sortie |
| AC Input Power | 2101 | W | Puissance AC en entrée (réseau) |
| AC Input And Output | 2278 | W | Flux AC parallèle entrée/sortie |
| Meter Power | 11016 | W | Puissance mesurée par le meter |
| Bypass Power | 667 | W | Puissance bypass |

#### Capteurs — Énergie cumulée

| Entité | Registre | Unité | Description |
|--------|----------|-------|-------------|
| Total AC Input Energy | 2107 | kWh | Énergie totale importée (valeur cluster) |
| Total AC Output Energy | 2104 | kWh | Énergie totale exportée (valeur cluster) |
| Battery Daily Charging Energy | 6004 | kWh | Charge quotidienne de la batterie |
| Battery Daily Discharging Energy| 6005 | kWh | Décharge quotidienne de la batterie |
| Battery Total Charging Energy | 6006 | kWh | Énergie totale chargée (lifetime) |
| Battery Total Discharging Energy | 6007 | kWh | Énergie totale déchargée (lifetime) |
| Rated Capacity | 142 | kWh | Capacité nominale de la batterie |

#### Capteurs — Batterie

| Entité | Registre | Unité | Description |
|--------|----------|-------|-------------|
| Battery Power | 6000 | W | Puissance batterie (+ charge / − décharge) |
| Battery State | 6001 | — | Static / Charging / Discharging |
| Battery SOC (Average) | 6002 | % | SOC moyen (cluster) |
| Battery % | 6009 | % | Niveau batterie Titan |
| Battery SOC | 6105 | % | SOC batterie (EPS) |
| Charging Power | 11009 | W | Puissance de charge instantanée |
| Discharging Power | 11011 | W | Puissance de décharge instantanée |
| Battery Temperature | 11042 | °C | Température de la batterie |
| Battery Cycles | 9003 | — | Nombre de cycles lifetime |
| Remaining Charging Time | 11019 | min | Temps de charge restant estimé |
| Residual Discharge Time | 11020 | min | Temps de décharge restant estimé |

#### Capteurs — Système

| Entité | Registre | Unité | Description |
|--------|----------|-------|-------------|
| Working Mode | 7101 | — | Mode de fonctionnement courant |
| Cluster State | 606 | — | Master / Slave / No Cluster |
| Meter Connection | 7120 | — | ON / OFF |
| Alarm | 8100 | — | Code alarme (128 types) |
| Backup State | 680 | — | OFF / ON |
| LEDs State | 7171 | — | OFF / ON |
| Device SN | 0 | — | Numéro de série |

#### Capteurs — Connectivité (diagnostics)

| Entité | Source | Description |
|--------|--------|-------------|
| WiFi RSSI | WiFi.GetConfig | Signal WiFi en dBm |
| WiFi SSID | WiFi.GetConfig | Nom du réseau WiFi |
| WiFi IP | WiFi.GetConfig | Adresse IP locale du Titan |
| MQTT Connection | Cloud.GetStatus | Connecté / Déconnecté |

#### Boutons

| Bouton | Mode | Description |
|--------|------|-------------|
| Start Charge | MR1 | Lance la charge avec les paramètres configurés |
| Start Discharge | MR1 | Lance la décharge avec les paramètres configurés |
| Standby | MR1 | Arrête charge/décharge |
| Realtime Mode | MR1 | Active le mode temps réel (requis pour les commandes locales) |
| Self-Consumed Mode | MR1 | Active le mode auto-consommation |
| Start Charge | Smart IA | Lance la charge via cloud |
| Start Discharge | Smart IA | Lance la décharge via cloud |
| Intelligent Mode | Smart IA | Active le mode intelligent cloud |
| Standby Mode | Smart IA | Met en veille via cloud |

#### Sliders (Number)

| Entité | Mode | Plage | Description |
|--------|------|-------|-------------|
| Charge/Discharge Power | MR1 | 0–800 W* | Puissance de charge/décharge |
| Charge SOC Limit | MR1 | 0–100 % | SOC maximum à atteindre en charge |
| SOC Security Min | MR1 | 5–100 % | SOC minimum avant arrêt décharge |
| Max Charge Power | MR1 | 50–800 W* | Limite de puissance de charge |
| Max Discharge Power | MR1 | 100–800 W* | Limite de puissance de décharge |
| Cloud Charge Power | Smart IA | 0–800 W* | Limite de charge cloud |
| Cloud Discharge Power | Smart IA | 0–800 W* | Limite de décharge cloud |

*800 W par Titan en mode standard, jusqu'à 2400 W en mode Override.

#### Interrupteurs (Switch)

| Entité | Registre | Description |
|--------|----------|-------------|
| Off-Grid | 7266 | Active/désactive le mode hors-réseau |
| LEDs | 7265 | Active/désactive les LEDs du Titan |

---

### Services

#### Mode MR1 (local)

| Service | Paramètres | Description |
|---------|------------|-------------|
| `izypower_titan.charge` | `power` (W), `soc_limit` (%) | Lance la charge |
| `izypower_titan.discharge` | `power` (W), `soc_limit` (%) | Lance la décharge |
| `izypower_titan.stop` | — | Arrête charge/décharge |
| `izypower_titan.set_realtime_mode` | — | Active le mode temps réel |
| `izypower_titan.set_selfconsumed_mode` | — | Active l'auto-consommation |
| `izypower_titan.set_intelligent_mode` | — | Active le mode intelligent |
| `izypower_titan.set_soc_security` | `value` (%) | Définit le SOC minimum de sécurité |
| `izypower_titan.set_max_power` | `value` (W) | Limite la puissance de charge |
| `izypower_titan.set_max_discharge_power` | `value` (W) | Limite la puissance de décharge |
| `izypower_titan.set_register_off_grid` | `value` (0/1) | Contrôle le mode hors-réseau |
| `izypower_titan.set_register_led` | `value` (0/1) | Contrôle les LEDs |
| `izypower_titan.cluster_rebalance` | `soc_security`, `max_charge_power`, `max_discharge_power` (au moins un) | Force tous les Titans du cluster à appliquer les mêmes valeurs — utile après une intervention manuelle ou pour remettre le cluster en cohérence |

#### Mode Smart IA (cloud)

| Service | Paramètres | Description |
|---------|------------|-------------|
| `izypower_titan.cloud_charge_manual` | `power` (W), `soc_limit` (%) | Charge manuelle via cloud |
| `izypower_titan.cloud_discharge_manual` | `power` (W) | Décharge manuelle via cloud |
| `izypower_titan.set_cloud_max_charge` | `power` (W) | Limite de charge cloud |
| `izypower_titan.set_cloud_max_discharge` | `power` (W) | Limite de décharge cloud |
| `izypower_titan.set_cloud_intelligent_mode` | — | Mode intelligent cloud |
| `izypower_titan.set_cloud_standby_mode` | — | Standby cloud |

Tous les services acceptent un paramètre optionnel `device_id` pour cibler un Titan spécifique dans un cluster.

---

### Cluster multi-Titans

L'intégration gère jusqu'à 3 Titans en cluster (1 Master + 2 Slaves).

- Les commandes cluster (`set_soc_security`, `set_max_power`, `set_max_discharge_power`) s'appliquent simultanément à tous les Titans
- En cas d'échec sur un Titan, les Titans déjà modifiés **reviennent automatiquement** à leur valeur précédente (rollback)
- Seul le Master expose les boutons et commandes de contrôle dans HA

Configuration requise : renseigner l'IP du Master et l'IP de chaque Slave lors de la configuration.

---

### Batteries Link

Les batteries Link (modules additionnels connectés au Titan) sont découvertes **automatiquement toutes les heures**.

Chaque batterie Link détectée expose les capteurs suivants :

| Capteur | Unité | Description |
|---------|-------|-------------|
| SN | — | Numéro de série |
| SOC | % | Niveau de charge |
| Temperature | °C | Température |
| Cycles | — | Nombre de cycles |

> Les nouvelles batteries ajoutées après le démarrage de l'intégration sont détectées et leurs entités créées **sans redémarrage de Home Assistant**.

---

### Tableau de bord Énergie (HA Energy Dashboard)

L'intégration expose nativement les `device_class` et `state_class` corrects pour s'intégrer au tableau de bord Énergie de Home Assistant.

**Configuration recommandée** :

1. **Paramètres → Tableaux de bord → Énergie**
2. Ajouter dans **Réseau électrique** :
   - *Énergie consommée du réseau* → `sensor.titan_total_ac_input_energy` (registre 2107)
   - *Énergie restituée au réseau* → `sensor.titan_total_ac_output_energy` (registre 2104)
3. Ajouter dans **Stockage par batterie** :
   - *Énergie sortie de la batterie* → `sensor.titan_battery_total_discharging_energy` (registre 6007)
   - *Énergie entrée dans la batterie* → `sensor.titan_battery_total_charging_energy` (registre 6006)
4. Optionnel — Production solaire si non gérée par un autre intégration : utiliser un `utility_meter` HA basé sur la somme des sensors PV (1664+1665+1666+1667).

> ⏱ Les valeurs sont des compteurs lifetime (`total_increasing`). HA peut prendre quelques minutes après l'ajout pour commencer à afficher les graphiques.

---

### Diagnostics

Depuis la v2.2.0, vous pouvez télécharger un rapport de diagnostic complet :

**Paramètres → Appareils et services → Izypower Titan → ⋮ → Télécharger les diagnostics**

Le fichier JSON contient :
- État de chaque coordinator (succès du dernier poll, erreurs consécutives, watchdog timestamp)
- Liste des batteries Link découvertes
- Données du dernier poll (avec credentials cloud, SSID et IP locale automatiquement masqués)
- Configuration sanitisée (mot de passe et username masqués)

Très utile pour le support — joignez ce fichier à toute issue GitHub.

---

##  Calibration BMS

L'intégration suit automatiquement la dernière charge complète confirmée de la batterie afin d'aider à la calibration du BMS (recommandée périodiquement pour éviter la dérive du SOC). Deux entités sont exposées par Titan.

### `binary_sensor` – Charge complète confirmée

Détecte qu'une charge complète **réelle** a eu lieu, et non un simple pic transitoire à 100 %.

- **État `on`** : charge complète confirmée (le délai de maintien a été atteint, la session est enregistrée).
- **État `off`** : condition non remplie, ou délai pas encore atteint.

**Condition de confirmation :**

| Registre | Description | Valeur requise |
| --- | --- | --- |
| `6002` | Battery SOC (Pile Average – moyenne cluster + Link) | ≥ 100 % |
| `6001` | Battery State | Static (1000) |

Les deux conditions doivent être tenues **simultanément et sans interruption** pendant au moins `full_charge_confirmation_minutes` minutes (voir options, défaut **10 min**). Toute perte de condition réinitialise le compteur.

**Attributs :**

| Attribut | Description |
| --- | --- |
| `confirmation_delay_min` | Délai de confirmation configuré (minutes) |
| `confirmation_progress_pct` | Progression vers la confirmation (0–100 %) |
| `confirmation_progress_s` | Temps écoulé depuis le début de la condition (secondes) |

**Événement Home Assistant :**

À chaque confirmation, l'intégration émet l'événement `izypower_titan_full_charge_confirmed`, exploitable dans vos automatisations :

```yaml
trigger:
  - platform: event
    event_type: izypower_titan_full_charge_confirmed
# Données : entry_id, host, serial_number, timestamp (ISO, heure locale)
```

### `sensor` – Jours depuis charge complète

Indique le nombre de **jours entiers** écoulés depuis la dernière charge complète confirmée.

- **Unité** : `j`
- **Valeur** : `0` si aucune charge complète n'a encore été confirmée depuis l'installation.
- Pas de `state_class` : la valeur se remet à zéro à chaque nouvelle charge complète, elle n'est donc pas destinée aux statistiques long terme.

**Attributs :**

| Attribut | Description |
| --- | --- |
| `last_full_charge` | Horodatage ISO de la dernière charge complète confirmée (`null` si jamais) |
| `calibration_recommended` | `true` lorsque la valeur dépasse **14 jours** |

> 💡 Le timestamp de la dernière charge complète est **persistant** : il survit aux redémarrages de Home Assistant (stocké dans `.storage`).

### ⚙️ Option de configuration

| Option | Description | Défaut |
| --- | --- | --- |
| `full_charge_confirmation_minutes` | Durée de maintien (SOC ≥ 100 % + State Static) requise pour valider une charge complète | `10` |

---

### Nouveautés v2.2.0

#### Corrections critiques
- **JWT Cloud** : le token était considéré valide même après expiration — les sessions cloud pouvaient rester bloquées silencieusement
- **JWT Cloud** : un token corrompu était considéré valide au lieu de forcer un re-login
- **Coordinator** : `is_cluster` ne plante plus si appelé avant le premier poll
- **Logs** : le message d'options updated affichait une erreur de formatage silencieuse à chaque modification

#### Nouvelles fonctionnalités
- **Reconfigure flow** : la configuration peut désormais être modifiée à tout moment depuis l'UI HA, sans supprimer/recréer l'intégration. Permet l'ajout/retrait dynamique de Titans, le changement d'IP, le basculement MR1 ↔ Smart IA, etc.
- **Diagnostics téléchargeables** : nouveau rapport JSON sanitisé téléchargeable depuis l'UI HA (Paramètres → Appareils → ⋮ → Télécharger les diagnostics) — très utile pour le support
- **Service `cluster_rebalance`** : nouveau service qui force tous les Titans d'un cluster à appliquer les mêmes valeurs (SOC security, max charge, max discharge) — utile après une intervention manuelle ou pour remettre le cluster en cohérence

#### Améliorations
- **Validation énergie** : après une absence réseau > 1 heure, les compteurs énergie acceptent la nouvelle valeur comme référence sans risque de faux positif
- **Batteries Link** : découverte automatique toutes les heures + création dynamique des entités sans redémarrage + découverte regroupée en 1 seule requête HTTP au lieu de 5
- **Cluster** : rollback automatique sur `set_soc_security`, `set_max_power`, `set_max_discharge_power` — en cas d'échec sur un Titan, les Titans déjà modifiés reviennent automatiquement à leur valeur précédente
- **Cluster** : pré-validation de l'accessibilité de tous les Titans avant exécution d'une commande cluster — abandon explicite plutôt qu'échec partiel
- **Watchdog** : si aucun poll réussi pendant 5 minutes, l'intégration passe explicitement en "indisponible" plutôt que de retourner indéfiniment des données obsolètes
- **Performance** : les capteurs WiFi (RSSI, SSID, IP) et le statut MQTT sont désormais pollés toutes les 60s au lieu de toutes les 5s — économie d'environ 30 000 requêtes HTTP par jour
- **Commandes** : suppression de la vérification de connexion meter — désormais gérée au niveau firmware Titan
- **Sécurité** : le mot de passe cloud n'apparaît plus dans les logs HA
- **Dépendances** : `pyjwt` n'est plus pinned strict (`>=2.10.1,<3`) — évite les conflits avec d'autres intégrations
- **Nettoyage** : suppression de code mort (`HOST_RE`, `async_set_soc`, imports inutilisés)


### Nouveautés v2.3.0
#### Nouveautés
- **Suivi de charge complète / calibration BMS** : ajout de deux entités par Titan
  - `binary_sensor` **Charge complète confirmée** — valide une charge réelle (SOC ≥ 100 % + état *Static* maintenus pendant le délai configuré, défaut 10 min) et émet l'événement `izypower_titan_full_charge_confirmed`.
  - `sensor` **Jours depuis charge complète** — nombre de jours depuis la dernière charge complète confirmée, avec attribut `calibration_recommended` (> 14 j). Timestamp persistant entre redémarrages.

#### Corrections / Améliorations
- **Battery Temperature** : migration de l'ID `9012` → `11042` (l'ancien ID ne remontait plus de valeur correcte).
- **Réactivation des capteurs d'énergie quotidienne** :
  - `Battery Daily Charging Energy` (ID `6004`)
  - `Battery Daily Discharging Energy` (ID `6005`)

---

---

## English

Home Assistant integration for **Izypower Titan** solar storage batteries.  
Supports local control (MR1), cloud control (Smart IA), multi-Titan clusters, and Link batteries.

### Table of contents

- [Features](#features)
- [Installation](#installation-1)
- [Configuration](#configuration-1)
- [Exposed entities](#exposed-entities)
- [Services](#services-1)
- [Multi-Titan cluster](#multi-titan-cluster)
- [Link batteries](#link-batteries)
- [BMS calibration](#bms-calibration)
- [What's new in v2.2.0](#whats-new-in-v220)

---

### Features

- Real-time monitoring of PV production, AC/DC power flows, and battery status
- Local control via RPC (MR1 mode) or cloud via the Izypower API (Smart IA mode)
- Cluster support for up to 3 Titans (Master + Slaves) with automatic rollback
- Automatic discovery of connected Link batteries (every hour)
- Intelligent energy data validation (protection against erroneous spikes)
- State restoration after HA restart

---

### Installation

#### Via HACS (recommended)

1. Open HACS → **Integrations** → ⋮ menu → **Custom repositories**
2. Add `https://github.com/khirale/izypower_titan` · Category: **Integration**
3. Search for **Izypower Titan** and click **Download**
4. Restart Home Assistant
5. **Settings → Devices & services → Add integration** → search *Izypower Titan*

#### Updating from a previous version

1. Remove the existing integration (Settings → Devices & services)
2. Restart Home Assistant
3. Update via HACS
4. Restart Home Assistant
5. Reconfigure the integration

#### Reconfiguring an existing integration

Since v2.2.0, the configuration can be modified at any time **without removing the integration**:

1. **Settings → Devices & services**
2. Open the **Izypower Titan** card → ⋮ menu → **Reconfigure**
3. All fields are pre-filled with current values — change what needs to change
4. The integration reloads automatically when finished

Supported scenarios:

| Scenario | Behaviour |
|---|---|
| Add a Titan (1→2, 2→3, 1→3) | Asks for the new slave IP(s) |
| Remove a Titan (3→2, 2→1, 3→1) | Removed slaves and their entities disappear |
| Change a Titan's IP | Pre-filled with the previous IP |
| Switch MR1 ↔ Smart IA | Asks for / skips cloud credentials |
| Toggle responsibility override | Respects the new value |
| Update cloud credentials | Username pre-filled, password to re-enter |

---

### Configuration

#### Connection mode

| Mode | Description | Requirements |
|------|-------------|--------------|
| **MR1 (Local)** | Direct RPC communication over LAN | Titan reachable on local network, default port 8080 |
| **Smart IA (Cloud)** | Control via the official Izypower API | Izypower account + internet connection |

#### Parameters

| Parameter | Description | Default |
|-----------|-------------|---------|
| IP address | Titan IP (or Master IP for clusters) | — |
| Port | Local RPC port | `8080` |
| Number of Titans | 1 to 3 | `1` |
| Responsibility mode | Standard (800 W/Titan) or Override (2400 W/Titan) | Standard |
| Poll interval | Update frequency in seconds | `5 s` |
| Cloud credentials | Email + password (Smart IA mode only) | — |

---

### Exposed entities

#### Sensors — PV production

| Entity | Register | Unit | Description |
|--------|----------|------|-------------|
| DC Input Power 1 | 1664 | W | PV 1 power |
| DC Input Power 2 | 1665 | W | PV 2 power |
| DC Input Power 3 | 1666 | W | PV 3 power |
| DC Input Power 4 | 1667 | W | PV 4 power |
| Total DC Output Power | 1501 | W | Total DC power output |

#### Sensors — AC flows

| Entity | Register | Unit | Description |
|--------|----------|------|-------------|
| AC Output Power | 2098 | W | AC output power |
| Total AC Output Power | 2108 | W | Total AC output power |
| AC Input Power | 2101 | W | AC input power (grid) |
| AC Input And Output | 2278 | W | Parallel AC input/output flow |
| Meter Power | 11016 | W | Meter-measured power |
| Bypass Power | 667 | W | Bypass power |

#### Sensors — Cumulative energy

| Entity | Register | Unit | Description |
|--------|----------|------|-------------|
| Total AC Input Energy | 2107 | kWh | Total imported energy (cluster value) |
| Total AC Output Energy | 2104 | kWh | Total exported energy (cluster value) |
| Battery Daily Charging Energy | 6004 | kWh | Daily Charging Energy |
| Battery Daily Discharging Energy| 6005 | kWh | Daily Discharging Energy |
| Battery Total Charging Energy | 6006 | kWh | Total lifetime charging energy |
| Battery Total Discharging Energy | 6007 | kWh | Total lifetime discharging energy |
| Rated Capacity | 142 | kWh | Nominal battery capacity |

#### Sensors — Battery

| Entity | Register | Unit | Description |
|--------|----------|------|-------------|
| Battery Power | 6000 | W | Battery power (+ charging / − discharging) |
| Battery State | 6001 | — | Static / Charging / Discharging |
| Battery SOC (Average) | 6002 | % | Average SOC (cluster) |
| Battery % | 6009 | % | Titan battery level |
| Battery SOC | 6105 | % | Battery SOC (EPS) |
| Charging Power | 11009 | W | Instantaneous charging power |
| Discharging Power | 11011 | W | Instantaneous discharging power |
| Battery Temperature | 11042 | °C | Battery temperature |
| Battery Cycles | 9003 | — | Lifetime cycle count |
| Remaining Charging Time | 11019 | min | Estimated time to full charge |
| Residual Discharge Time | 11020 | min | Estimated remaining discharge time |

#### Sensors — System

| Entity | Register | Unit | Description |
|--------|----------|------|-------------|
| Working Mode | 7101 | — | Current operating mode |
| Cluster State | 606 | — | Master / Slave / No Cluster |
| Meter Connection | 7120 | — | ON / OFF |
| Alarm | 8100 | — | Alarm code (128 types) |
| Backup State | 680 | — | OFF / ON |
| LEDs State | 7171 | — | OFF / ON |
| Device SN | 0 | — | Serial number |

#### Sensors — Connectivity (diagnostics)

| Entity | Source | Description |
|--------|--------|-------------|
| WiFi RSSI | WiFi.GetConfig | WiFi signal strength in dBm |
| WiFi SSID | WiFi.GetConfig | WiFi network name |
| WiFi IP | WiFi.GetConfig | Titan local IP address |
| MQTT Connection | Cloud.GetStatus | Connected / Disconnected |

#### Buttons

| Button | Mode | Description |
|--------|------|-------------|
| Start Charge | MR1 | Start charging with configured parameters |
| Start Discharge | MR1 | Start discharging with configured parameters |
| Standby | MR1 | Stop charge/discharge |
| Realtime Mode | MR1 | Enable realtime mode (required for local commands) |
| Self-Consumed Mode | MR1 | Enable self-consumption mode |
| Start Charge | Smart IA | Start charging via cloud |
| Start Discharge | Smart IA | Start discharging via cloud |
| Intelligent Mode | Smart IA | Enable cloud intelligent mode |
| Standby Mode | Smart IA | Set standby via cloud |

#### Sliders (Number)

| Entity | Mode | Range | Description |
|--------|------|-------|-------------|
| Charge/Discharge Power | MR1 | 0–800 W* | Charge/discharge power |
| Charge SOC Limit | MR1 | 0–100 % | Maximum SOC target when charging |
| SOC Security Min | MR1 | 5–100 % | Minimum SOC before discharge stops |
| Max Charge Power | MR1 | 50–800 W* | Charge power limit |
| Max Discharge Power | MR1 | 100–800 W* | Discharge power limit |
| Cloud Charge Power | Smart IA | 0–800 W* | Cloud charge power limit |
| Cloud Discharge Power | Smart IA | 0–800 W* | Cloud discharge power limit |

*800 W per Titan in standard mode, up to 2400 W in Override mode.

#### Switches

| Entity | Register | Description |
|--------|----------|-------------|
| Off-Grid | 7266 | Enable/disable off-grid mode |
| LEDs | 7265 | Enable/disable Titan LEDs |

---

### Services

#### MR1 mode (local)

| Service | Parameters | Description |
|---------|------------|-------------|
| `izypower_titan.charge` | `power` (W), `soc_limit` (%) | Start charging |
| `izypower_titan.discharge` | `power` (W), `soc_limit` (%) | Start discharging |
| `izypower_titan.stop` | — | Stop charge/discharge |
| `izypower_titan.set_realtime_mode` | — | Enable realtime mode |
| `izypower_titan.set_selfconsumed_mode` | — | Enable self-consumption mode |
| `izypower_titan.set_intelligent_mode` | — | Enable intelligent mode |
| `izypower_titan.set_soc_security` | `value` (%) | Set minimum security SOC |
| `izypower_titan.set_max_power` | `value` (W) | Set charge power limit |
| `izypower_titan.set_max_discharge_power` | `value` (W) | Set discharge power limit |
| `izypower_titan.set_register_off_grid` | `value` (0/1) | Control off-grid mode |
| `izypower_titan.set_register_led` | `value` (0/1) | Control LEDs |
| `izypower_titan.cluster_rebalance` | `soc_security`, `max_charge_power`, `max_discharge_power` (at least one) | Force all cluster Titans to apply the same values — useful after manual intervention or to bring the cluster back to consistency |

#### Smart IA mode (cloud)

| Service | Parameters | Description |
|---------|------------|-------------|
| `izypower_titan.cloud_charge_manual` | `power` (W), `soc_limit` (%) | Manual charge via cloud |
| `izypower_titan.cloud_discharge_manual` | `power` (W) | Manual discharge via cloud |
| `izypower_titan.set_cloud_max_charge` | `power` (W) | Cloud charge power limit |
| `izypower_titan.set_cloud_max_discharge` | `power` (W) | Cloud discharge power limit |
| `izypower_titan.set_cloud_intelligent_mode` | — | Cloud intelligent mode |
| `izypower_titan.set_cloud_standby_mode` | — | Cloud standby |

All services accept an optional `device_id` parameter to target a specific Titan in a cluster.

---

### Multi-Titan cluster

The integration supports clusters of up to 3 Titans (1 Master + 2 Slaves).

- Cluster commands (`set_soc_security`, `set_max_power`, `set_max_discharge_power`) apply simultaneously to all Titans
- If a command fails on one Titan, already-modified Titans **automatically revert** to their previous value (rollback)
- Only the Master exposes control buttons and commands in HA

Setup: enter the Master IP and each Slave IP during integration configuration.

---

### Link batteries

Link batteries (additional modules connected to the Titan) are **automatically discovered every hour**.

Each detected Link battery exposes the following sensors:

| Sensor | Unit | Description |
|--------|------|-------------|
| SN | — | Serial number |
| SOC | % | State of charge |
| Temperature | °C | Temperature |
| Cycles | — | Lifetime cycle count |

> Batteries added after the integration starts are detected and their entities created **without restarting Home Assistant**.

---

### Energy Dashboard (HA Energy Dashboard)

The integration natively exposes the correct `device_class` and `state_class` to integrate with Home Assistant's Energy Dashboard.

**Recommended setup**:

1. **Settings → Dashboards → Energy**
2. Add under **Electricity grid**:
   - *Grid consumption* → `sensor.titan_total_ac_input_energy` (register 2107)
   - *Return to grid* → `sensor.titan_total_ac_output_energy` (register 2104)
3. Add under **Home battery storage**:
   - *Energy going out of the battery* → `sensor.titan_battery_total_discharging_energy` (register 6007)
   - *Energy going into the battery* → `sensor.titan_battery_total_charging_energy` (register 6006)
4. Optional — Solar production if not handled by another integration: use a HA `utility_meter` based on the sum of the PV sensors (1664+1665+1666+1667).

> ⏱ Values are lifetime counters (`total_increasing`). HA may take a few minutes after adding before graphs start populating.

---

### Diagnostics

Since v2.2.0, you can download a full diagnostics report:

**Settings → Devices & services → Izypower Titan → ⋮ → Download diagnostics**

The JSON file contains:
- State of each coordinator (last poll success, consecutive errors, watchdog timestamp)
- List of discovered Link batteries
- Last poll data (with cloud credentials, SSID and local IP automatically redacted)
- Sanitized configuration (password and username redacted)

Very useful for support — attach this file to any GitHub issue.

---

##  BMS Calibration

The integration automatically tracks the battery's last confirmed full charge, helping with periodic BMS calibration (recommended to prevent SOC drift). Two entities are exposed per Titan.

### `binary_sensor` – Full charge confirmed

Detects that a **real** full charge occurred, rather than a brief transient spike to 100 %.

- **State `on`**: full charge confirmed (hold delay reached, session recorded).
- **State `off`**: condition not met, or delay not yet reached.

**Confirmation condition:**

| Register | Description | Required value |
| --- | --- | --- |
| `6002` | Battery SOC (Pile Average – cluster + Link average) | ≥ 100 % |
| `6001` | Battery State | Static (1000) |

Both conditions must be held **simultaneously and without interruption** for at least `full_charge_confirmation_minutes` minutes (see options, default **10 min**). Any loss of condition resets the timer.

**Attributes:**

| Attribute | Description |
| --- | --- |
| `confirmation_delay_min` | Configured confirmation delay (minutes) |
| `confirmation_progress_pct` | Progress toward confirmation (0–100 %) |
| `confirmation_progress_s` | Elapsed time since the condition started (seconds) |

**Home Assistant event:**

On each confirmation, the integration fires the `izypower_titan_full_charge_confirmed` event, usable in your automations:

```yaml
trigger:
  - platform: event
    event_type: izypower_titan_full_charge_confirmed
# Data: entry_id, host, serial_number, timestamp (ISO, local time)
```

### `sensor` – Days since full charge

Reports the number of **whole days** since the last confirmed full charge.

- **Unit**: `j`
- **Value**: `0` if no full charge has been confirmed yet since installation.
- No `state_class`: the value resets to zero on every new full charge, so it is not intended for long-term statistics.

**Attributes:**

| Attribute | Description |
| --- | --- |
| `last_full_charge` | ISO timestamp of the last confirmed full charge (`null` if never) |
| `calibration_recommended` | `true` when the value exceeds **14 days** |

> 💡 The last full-charge timestamp is **persistent**: it survives Home Assistant restarts (stored in `.storage`).

### ⚙️ Configuration option

| Option | Description | Default |
| --- | --- | --- |
| `full_charge_confirmation_minutes` | Hold duration (SOC ≥ 100 % + Static state) required to validate a full charge | `10` |

---

### What's new in v2.2.0

#### Critical fixes
- **Cloud JWT** : token was considered valid even after expiration — cloud sessions could silently stall without re-login
- **Cloud JWT** : a corrupted token was considered valid instead of forcing a re-login
- **Coordinator** : `is_cluster` no longer crashes if called before the first poll
- **Logs** : the options-updated log message was silently throwing a formatting error on every change

#### New features
- **Reconfigure flow** : the configuration can now be modified at any time from the HA UI, without removing/recreating the integration. Supports dynamic Titan add/remove, IP changes, switching MR1 ↔ Smart IA, etc.
- **Downloadable diagnostics** : new sanitized JSON report downloadable from the HA UI (Settings → Devices → ⋮ → Download diagnostics) — very useful for support
- **`cluster_rebalance` service** : new service that forces all Titans in a cluster to apply the same values (SOC security, max charge, max discharge) — useful after manual intervention or to bring the cluster back into consistency

#### Improvements
- **Energy validation** : after a network absence > 1 hour, energy counters accept the new value as a fresh baseline without false positive risk
- **Link batteries** : automatic hourly rediscovery + dynamic entity creation without HA restart + grouped discovery in 1 HTTP request instead of 5
- **Cluster** : automatic rollback on `set_soc_security`, `set_max_power`, `set_max_discharge_power` — if a command fails on one Titan, already-modified Titans automatically revert to their previous value
- **Cluster** : pre-validation of all Titans' availability before executing a cluster command — explicit abort instead of partial failure
- **Watchdog** : if no successful poll for 5 minutes, the integration explicitly goes "unavailable" instead of indefinitely returning stale data
- **Performance** : WiFi sensors (RSSI, SSID, IP) and MQTT status are now polled every 60s instead of every 5s — saves around 30 000 HTTP requests per day
- **Commands** : removed meter connection check — now handled at Titan firmware level
- **Security** : cloud password no longer appears in HA logs
- **Dependencies** : `pyjwt` is no longer pinned strict (`>=2.10.1,<3`) — avoids conflicts with other integrations
- **Cleanup** : removed dead code (`HOST_RE`, `async_set_soc`, unused imports)

---

## License

MIT — © [khirale](https://github.com/khirale)
