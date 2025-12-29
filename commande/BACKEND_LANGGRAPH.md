# Commandes - Backend LangGraph

## Description

Service LangGraph pour OCR, mapping et extraction LLM (port 8002).

- **Port** : 8002
- **URL** : http://localhost:8002
- **Health Check** : http://localhost:8002/health

## Prérequis

- Python 3.10.9
- Environnement virtuel activé
- Dépendances installées (`pip install -r requirements.txt`)
- **Clés API LLM** (si MOCK_MODE=false) :
  - `OPENAI_API_KEY` ou
  - `ANTHROPIC_API_KEY`

## Commandes de Démarrage

### Démarrage Manuel

#### Windows (PowerShell)
```powershell
cd backend-langgraph
.\venv\Scripts\activate
uvicorn app.main:app --reload --port 8002
```

#### Linux/Mac
```bash
cd backend-langgraph
source venv/bin/activate
uvicorn app.main:app --reload --port 8002
```

### Démarrage avec Docker

```bash
docker-compose up backend-langgraph
```

Ou depuis la racine du projet :
```bash
docker-compose up -d backend-langgraph
```

## Configuration

### Variables d'Environnement Importantes

Créer un fichier `.env` dans `backend-langgraph/` :

```env
# Application
LOG_LEVEL=INFO
LOG_FORMAT=console

# Server
HOST=0.0.0.0
PORT=8002

# Mock Mode (pour tests sans LLM API)
MOCK_MODE=true

# API Keys (si MOCK_MODE=false)
# OPENAI_API_KEY=your_key_here
# ANTHROPIC_API_KEY=your_key_here
```

### Mode Mock

Pour les tests sans clés API LLM, définir `MOCK_MODE=true` dans le `.env`.

## Vérification

### Health Check
```bash
curl http://localhost:8002/health
```

Ou dans un navigateur : http://localhost:8002/health

### Test Endpoint Principal
```bash
curl -X POST http://localhost:8002/api/langgraph/process-mcp-request \
  -H "Content-Type: application/json" \
  -d '{
    "record_id": "001XX000001",
    "session_id": null,
    "user_request": "Extract data from documents",
    "documents": [...],
    "fields_dictionary": {...}
  }'
```

## Endpoints Principaux

- `POST /api/langgraph/process-mcp-request` : Traite une requête MCP avec LangGraph
- `GET /health` : Health check

## Arrêt du Service

### Si démarré manuellement
- Appuyer sur `Ctrl+C` dans le terminal

### Si démarré avec Docker
```bash
docker-compose stop backend-langgraph
```

Ou pour arrêter et supprimer le conteneur :
```bash
docker-compose down backend-langgraph
```

## Logs

Les logs s'affichent dans la console où le service a été démarré.

Pour Docker :
```bash
docker-compose logs -f backend-langgraph
```

## Timeout

Le service LangGraph utilise un timeout de **120 secondes** pour le traitement complet (OCR + mapping + extraction LLM).

