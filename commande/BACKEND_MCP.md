# Commandes - Backend MCP

## Description

Service MCP orchestrant le workflow complet (port 8000).

- **Port** : 8000
- **URL** : http://localhost:8000
- **Health Check** : http://localhost:8000/health

## Prérequis

- Python 3.10.9
- Environnement virtuel activé
- Dépendances installées (`pip install -r requirements.txt`)
- **Mock Salesforce démarré** (port 8001)
- **Backend LangGraph démarré** (port 8002) - optionnel pour certains endpoints

## Commandes de Démarrage

### Démarrage Manuel

#### Windows (PowerShell)
```powershell
cd backend-mcp
.\venv\Scripts\activate
uvicorn app.main:app --reload --port 8000
```

#### Linux/Mac
```bash
cd backend-mcp
source venv/bin/activate
uvicorn app.main:app --reload --port 8000
```

### Démarrage avec Docker

```bash
docker-compose up backend-mcp
```

Ou depuis la racine du projet :
```bash
docker-compose up -d backend-mcp
```

## Configuration

### Variables d'Environnement Importantes

Créer un fichier `.env` dans `backend-mcp/` :

```env
# Application
LOG_LEVEL=INFO
LOG_FORMAT=console

# Server
HOST=0.0.0.0
PORT=8000

# External Services
MOCK_SALESFORCE_URL=http://localhost:8001
SALESFORCE_REQUEST_TIMEOUT=5.0

# Session Storage (SQLite)
SESSION_DB_PATH=data/sessions.db
SESSION_TTL_SECONDS=86400

# LangGraph
LANGGRAPH_URL=http://localhost:8002
LANGGRAPH_TIMEOUT=120.0
```

## Vérification

### Health Check
```bash
curl http://localhost:8000/health
```

Ou dans un navigateur : http://localhost:8000/health

### Test Endpoint Principal
```bash
curl -X POST http://localhost:8000/api/mcp/receive-request \
  -H "Content-Type: application/json" \
  -d '{
    "record_id": "001XX000001",
    "session_id": null,
    "user_message": "Extract data from documents"
  }'
```

## Endpoints Principaux

- `POST /api/mcp/receive-request` : Endpoint principal recevant les requêtes Salesforce
- `POST /api/mcp/request-salesforce-data` : Endpoint interne pour récupérer les données Salesforce
- `GET /api/task-status/{task_id}` : Statut des tâches async
- `GET /health` : Health check

## Arrêt du Service

### Si démarré manuellement
- Appuyer sur `Ctrl+C` dans le terminal

### Si démarré avec Docker
```bash
docker-compose stop backend-mcp
```

Ou pour arrêter et supprimer le conteneur :
```bash
docker-compose down backend-mcp
```

## Logs

Les logs s'affichent dans la console où le service a été démarré.

Pour Docker :
```bash
docker-compose logs -f backend-mcp
```

## Base de Données SQLite

La base de données SQLite est stockée dans `backend-mcp/data/sessions.db`.

Pour inspecter la base de données :
```bash
cd backend-mcp
python scripts/inspect_sessions_db.py
```

