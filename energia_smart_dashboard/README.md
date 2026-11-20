# ENERGIA — Smart Energy Dashboard

Application Streamlit d'aide à la décision pour un acheteur d'énergie de collectivité en Centre-Val de Loire.

## Décision métier

Choisir les quatre heures consécutives les plus favorables pour décaler la recharge d'une flotte électrique, en recherchant une consommation régionale historiquement faible et une contribution renouvelable élevée.

## Fonctionnalités

- Filtres globaux : période et type de jour (semaine / week-end).
- KPI calculés sur la vue filtrée.
- Profil de consommation par demi-heure et type de jour.
- Comparaison des pics saisonniers.
- Classement des créneaux de quatre heures.
- Part renouvelable par heure et par mois.
- Drill-down : année → mois → jour → demi-heure.
- Couche ML : Random Forest de prévision de la consommation, split chronologique, MAE/RMSE et baseline.

## Données

Fichier : `data/energie.parquet`  
Source : RTE, éCO2mix régional, données définitives.  
Licence : Licence Ouverte 2.0 (Etalab).  
Période annoncée : 01/09/2023 au 31/08/2026, 52 603 demi-heures.

Téléchargement :
```bash
python scripts/download_data.py
```

Le fichier Parquet n'est pas inclus dans ce dépôt généré. Le script ci-dessus le télécharge depuis le dépôt public de l'énoncé. Ne pas ajouter de données personnelles.

## Installation locale

```bash
uv venv
# Windows PowerShell
.venv\Scripts\Activate.ps1
# Linux / macOS
source .venv/bin/activate

uv pip install -r requirements.txt
python scripts/download_data.py
streamlit run app.py
```

Alternative avec pip :
```bash
python -m venv .venv
pip install -r requirements.txt
python scripts/download_data.py
streamlit run app.py
```

## Tests et qualité

```bash
pytest
ruff check .
```

## Méthode de calcul

- Les heures sont affichées en heure de Paris via la colonne `heure` fournie par le jeu de données.
- Une demi-heure est une puissance moyenne en MW ; l'énergie correspondante est MW × 0,5 MWh.
- Les renouvelables sont définies ici comme éolien + solaire + hydraulique + bioénergies.
- Le créneau de 4 h correspond à 8 demi-heures consécutives d'une même journée.
- Score indicatif : 70 % demande faible + 30 % part renouvelable élevée. Ce score est un choix de priorisation métier, à valider avec l'acheteur d'énergie.
- Le modèle ML utilise uniquement des variables calendaires. Il s'agit d'une première baseline pédagogique : il ne prédit pas les prix, ni la disponibilité réelle, ni la météo.

## Limites à expliquer à la soutenance

1. La consommation régionale n'est pas la consommation du bâtiment ou du dépôt de la collectivité.
2. Une forte part renouvelable ne garantit pas un prix spot bas ni une capacité locale disponible.
3. Le classement historique ne tient pas compte de la puissance des bornes, des contraintes de départ des véhicules, ni du contrat fournisseur.
4. La prévision ML n'intègre pas la température ; une amélioration pertinente serait de joindre les données Météo-France.
5. Les résultats doivent être recalculés après contrôle des valeurs manquantes et des éventuelles données consolidées.

## Assistant de code

Assistant utilisé : ChatGPT, pour cadrer la décision métier, proposer l'architecture, générer une première base de code et documenter les calculs. Le code doit être relu, testé et expliqué par chaque membre du groupe avant la soutenance.


## Assistant conversationnel IA (Groq)

L'onglet **Assistant IA** permet de poser des questions en langage naturel sur la vue filtrée du dashboard. L'application calcule d'abord des agrégats fiables (consommation, heures creuses, pics saisonniers, part renouvelable et créneaux de quatre heures), puis les transmet au LLM. Les lignes brutes du Parquet ne sont pas envoyées au modèle.

### Configuration locale

Créer une clé sur https://console.groq.com/keys, puis la définir dans l'environnement du processus FastAPI avec `GROQ_API_KEY`. Le tableau de bord Streamlit contacte l'API REST ; la clé ne doit donc pas être placée dans le navigateur ni dans les secrets de l'interface. Voir la section **Architecture API REST + serveur MCP** ci-dessous pour les commandes de démarrage. `GROQ_MODEL` permet de choisir le modèle sans modifier le code.

### Périmètre et sécurité

- L'assistant répond à partir des agrégats de la période et des filtres sélectionnés.
- Il ne reçoit pas les 52 603 lignes brutes ; seuls des indicateurs synthétiques lui sont transmis.
- La clé API est lue depuis l'environnement du serveur FastAPI, jamais codée en dur ni transmise au navigateur.
- Les réponses ne remplacent pas une étude tarifaire ou les contraintes locales des bornes.
- Vérifier les conditions et quotas du fournisseur Groq avant la démonstration.

## Déploiement Streamlit Community Cloud

1. Pousser le dépôt GitHub avec `app.py`, `src/`, `scripts/`, `tests/`, `requirements.txt` et `data/energie.parquet`.
2. Créer une application sur Streamlit Community Cloud.
3. Choisir `app.py` comme fichier principal.
4. Vérifier que le Parquet est présent dans le dépôt et que sa taille respecte les limites de la plateforme.
5. Copier l'URL publique dans cette section du README.

URL de démonstration : à compléter après déploiement.

## Source

RTE, éCO2mix régional, données définitives — Licence Ouverte 2.0.
https://opendata.reseaux-energies.fr/explore/dataset/eco2mix-regional-cons-def/

## Architecture API REST + serveur MCP

Le projet sépare désormais l'interface, les services métier et les points d'accès IA :

```text
Navigateur
   │
   ▼
Streamlit (8501) ──HTTP/JSON──► FastAPI (8000) ──► Services ENERGIA ──► energie.parquet
                                      │
                                      └──► Groq (LLM)

Agent compatible MCP ──Streamable HTTP──► Serveur MCP (8001)
                                             │
                                             └──► mêmes Services ENERGIA
```

### 1. Démarrer l'API REST

Installer les dépendances :

```bash
pip install -r requirements.txt
python scripts/download_data.py
```

Définir la clé Groq dans le terminal qui lancera FastAPI (ne pas la mettre dans Git) :

**Windows PowerShell :**
```powershell
$env:GROQ_API_KEY="votre_cle_groq"
$env:GROQ_MODEL="llama-3.3-70b-versatile"
uvicorn api:app --host 127.0.0.1 --port 8000 --reload
```

**Linux / macOS :**
```bash
export GROQ_API_KEY="votre_cle_groq"
export GROQ_MODEL="llama-3.3-70b-versatile"
uvicorn api:app --host 127.0.0.1 --port 8000 --reload
```

Documentation interactive : http://127.0.0.1:8000/docs  
Contrôle de santé : http://127.0.0.1:8000/health

### 2. Endpoints REST disponibles

| Méthode | Endpoint | Rôle |
|---|---|---|
| GET | `/health` | Vérifier l'état de l'API et le chargement des données |
| GET | `/api/v1/summary` | KPI et meilleur créneau de 4 h |
| GET | `/api/v1/slots?limit=5` | Classement des créneaux de recharge |
| GET | `/api/v1/profile` | Profil de consommation par heure et type de jour |
| GET | `/api/v1/seasonal-peaks` | Pics de consommation par saison |
| GET | `/api/v1/renewables` | Profil de production renouvelable |
| POST | `/api/v1/assistant/chat` | Question en langage naturel à l'agent IA |

Les endpoints analytiques acceptent les paramètres `start_date`, `end_date` (format `YYYY-MM-DD`) et `day_types` (`semaine`, `week-end`). Exemple :

```bash
curl "http://127.0.0.1:8000/api/v1/summary?start_date=2025-01-01&end_date=2025-03-31&day_types=semaine"
```

Exemple de requête à l'assistant :

```bash
curl -X POST "http://127.0.0.1:8000/api/v1/assistant/chat" \
  -H "Content-Type: application/json" \
  -d '{"question":"Quel est le meilleur créneau de recharge de quatre heures ?","day_types":["semaine","week-end"]}'
```

L'onglet Streamlit envoie désormais les questions à cette API. Par défaut, il utilise `http://127.0.0.1:8000`. Pour changer l'adresse, définir `ENERGIA_API_URL` dans l'environnement du processus Streamlit.

### 3. Démarrer le serveur MCP

Dans un deuxième terminal, à la racine du projet :

```bash
python mcp_server.py
```

Le serveur MCP utilise le transport **Streamable HTTP** sur `http://127.0.0.1:8001/mcp`. Il expose les outils suivants à un agent ou client compatible MCP :

- `get_energy_summary` : indicateurs synthétiques de la période.
- `find_best_charging_slots` : classement des créneaux consécutifs de quatre heures.
- `get_consumption_profile` : profil de consommation par heure.
- `get_seasonal_consumption_peaks` : pics saisonniers.
- `get_renewable_production_profile` : part renouvelable selon l'heure.

Pour tester la connexion, ouvrir [MCP Inspector](https://github.com/modelcontextprotocol/inspector) et le connecter à `http://127.0.0.1:8001/mcp` en Streamable HTTP. Un agent compatible MCP peut alors découvrir les outils et les appeler. Le serveur MCP et l'API REST réutilisent les mêmes fonctions métier : les calculs restent cohérents.

### 4. Démarrage complet en local

Ouvrir trois terminaux depuis le dossier du projet :

| Terminal | Commande | Port |
|---|---|---|
| 1 — API | `uvicorn api:app --reload --port 8000` | 8000 |
| 2 — MCP | `python mcp_server.py` | 8001 |
| 3 — Interface | `streamlit run app.py` | 8501 |

Configurer `GROQ_API_KEY` dans le terminal 1 avant de démarrer l'API. Le serveur MCP donne accès aux outils de données ; il n'a pas besoin de clé Groq.

### Sécurité et déploiement

- En local, les services écoutent sur `127.0.0.1` ; ne pas exposer directement ces ports sur Internet.
- Pour un déploiement public, ajouter une authentification (par exemple OAuth2/JWT), HTTPS, CORS avec une liste d'origines autorisées, limitation de débit et journalisation.
- Ne jamais publier `GROQ_API_KEY`, ne pas l'envoyer au navigateur et ne pas la placer dans le dépôt Git.
- Le serveur MCP expose des outils de lecture seule ; il ne modifie pas les données.
- En production, placer l'API et MCP derrière un reverse proxy et gérer les secrets via les variables d'environnement de la plateforme.
