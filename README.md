# OptiClaims - Backend Application

Application backend pour le traitement intelligent de sinistres avec intégration Salesforce et agent GenAI LangGraph.

## Architecture

Le projet est organisé en microservices :

- **backend-mcp** : Service MCP (endpoints d'interaction avec Salesforce)
- **mock-salesforce** : Service mock pour simuler les interactions Salesforce
- **backend-langgraph** : Service LangGraph (agent GenAI) - à venir
- **monitoring** : Système de monitoring - à venir

## Structure du projet

```
sfd-clm/
├── backend-mcp/          # Service MCP
├── mock-salesforce/      # Service mock Salesforce
├── backend-langgraph/    # Service LangGraph (à venir)
├── monitoring/           # Monitoring (à venir)
└── shared/              # Code partagé
```

## Installation

### Prérequis

- Python 3.11+
- pip

### Installation des dépendances

```bash
# Backend MCP
cd backend-mcp
pip install -r requirements.txt

# Mock Salesforce
cd ../mock-salesforce
pip install -r requirements.txt
```

## Configuration

Copiez les fichiers `.env.example` et configurez les variables d'environnement :

```bash
cp backend-mcp/.env.example backend-mcp/.env
cp mock-salesforce/.env.example mock-salesforce/.env
```

## Démarrage

### Service Mock Salesforce

```bash
cd mock-salesforce
uvicorn app.main:app --reload --port 8001
```

### Service Backend MCP

```bash
cd backend-mcp
uvicorn app.main:app --reload --port 8000
```

## Endpoints

### Mock Salesforce

- `POST /mock/salesforce/get-record-data` : Récupère les données mock pour un record_id

### Backend MCP

- `POST /api/mcp/receive-request` : Endpoint principal recevant les requêtes Salesforce
- `POST /api/mcp/request-salesforce-data` : Endpoint interne pour récupérer les données Salesforce

## Testing

### Quick Test

Run the simplified test to quickly validate the pipeline:

```bash
python tests/test_pipeline_simple.py
```

### Full E2E Test

1. **Start services:**
   ```bash
   # Unix/Linux/Mac
   ./tests/start_services.sh
   
   # Windows
   tests\start_services.bat
   ```

2. **Run tests:**
   ```bash
   # Quick test
   python tests/test_pipeline_simple.py
   
   # Full E2E test
   python tests/test_pipeline_e2e.py
   
   # Component tests
   python tests/test_workflow_components.py
   ```

See `tests/README.md` and `tests/QUICK_START.md` for detailed testing instructions.

## Tests

```bash
pytest
```

## Documentation

### Documentation Complète du Pipeline

Pour une documentation détaillée du pipeline avec tous les endpoints, formats d'inputs/outputs, diagrammes de flux et exemples de test :

- **[Documentation Complète du Pipeline](docs/PIPELINE_DOCUMENTATION.md)** : Documentation exhaustive avec diagrammes, formats de données, et scénarios de test
- **[Exemples de Test](docs/TEST_EXAMPLES.md)** : Exemples concrets et scripts prêts à l'emploi pour tester tous les endpoints

### Plans de Développement

Voir le plan de développement dans `.cursor/plans/` pour les détails d'implémentation.

