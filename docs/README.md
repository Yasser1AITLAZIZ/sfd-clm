# Documentation OptiClaims

Ce dossier contient la documentation complète du pipeline OptiClaims.

## Fichiers de Documentation

### [PIPELINE_DOCUMENTATION.md](PIPELINE_DOCUMENTATION.md)

Documentation complète et exhaustive du pipeline OptiClaims incluant :

- **État d'avancement du projet** : Statut de tous les services et composants
- **Architecture du pipeline** : Diagrammes de flux Mermaid
- **Documentation des endpoints** : 
  - Formats d'input exacts (JSON)
  - Formats d'output attendus (JSON)
  - Exemples de test avec curl
  - Codes d'erreur
- **Diagrammes de flux détaillés** : Workflow Orchestrator
- **Données mock disponibles** : Tous les record_ids et exemples
- **Scénarios de test complets** : Workflows end-to-end
- **Structure des données** : Formats Document, Field, Session
- **Prochaines étapes** : Roadmap d'implémentation

### [TEST_EXAMPLES.md](TEST_EXAMPLES.md)

Exemples pratiques et scripts prêts à l'emploi pour tester le pipeline :

- **Tests par endpoint** : Exemples curl pour chaque endpoint
- **Scénarios de test complets** : Workflows complets avec plusieurs étapes
- **Scripts automatisés** : Scripts Bash et Python pour tests automatisés
- **Vérification des résultats** : Comment vérifier les logs, Redis, réponses
- **Notes techniques** : Conseils et bonnes pratiques

## Navigation Rapide

### Pour comprendre l'architecture
→ Lire [PIPELINE_DOCUMENTATION.md](PIPELINE_DOCUMENTATION.md) - Section "Architecture du Pipeline"

### Pour tester les endpoints
→ Lire [TEST_EXAMPLES.md](TEST_EXAMPLES.md) - Section "Tests par Endpoint"

### Pour comprendre les formats de données
→ Lire [PIPELINE_DOCUMENTATION.md](PIPELINE_DOCUMENTATION.md) - Section "Structure des Données"

### Pour exécuter des tests automatisés
→ Lire [TEST_EXAMPLES.md](TEST_EXAMPLES.md) - Section "Scripts de Test Automatisés"

## Endpoints Principaux

### Mock Salesforce (Port 8001)
- `POST /mock/salesforce/get-record-data` : Récupération données mock
- `POST /mock/apex/send-user-request` : Simulation requête Apex
- `GET /health` : Health check

### Backend MCP (Port 8000)
- `POST /api/mcp/receive-request` : Endpoint principal (workflow orchestrator)
- `POST /api/mcp/request-salesforce-data` : Récupération données Salesforce
- `GET /api/task-status/{task_id}` : Statut des tâches async
- `GET /health` : Health check

## Quick Start

1. **Démarrer les services** :
```bash
# Terminal 1 - Mock Salesforce
cd mock-salesforce
uvicorn app.main:app --reload --port 8001

# Terminal 2 - Backend MCP
cd backend-mcp
uvicorn app.main:app --reload --port 8000
```

2. **Tester un endpoint** :
```bash
curl -X POST http://localhost:8001/mock/salesforce/get-record-data \
  -H "Content-Type: application/json" \
  -d '{"record_id": "001XX000001"}'
```

3. **Voir les exemples complets** : [TEST_EXAMPLES.md](TEST_EXAMPLES.md)

## Données Mock Disponibles

| Record ID | Type | Documents | Champs |
|-----------|------|-----------|--------|
| 001XX000001 | Claim | 2 (PDF + JPG) | 4 |
| 001XX000002 | Claim | 1 (PDF) | 3 |
| 001XX000003 | Claim | 2 (PDF + ZIP) | 4 |
| 001XX000004 | Claim | 1 (PDF) | 3 |
| 001XX000005 | Claim | 2 (PDF + PDF) | 3 |

Voir [PIPELINE_DOCUMENTATION.md](PIPELINE_DOCUMENTATION.md) pour les détails complets.

## Codes d'Erreur

| Code | HTTP Status | Description |
|------|-------------|-------------|
| INVALID_REQUEST | 400 | Format de requête invalide |
| INVALID_RECORD_ID | 400 | record_id vide ou invalide |
| RECORD_NOT_FOUND | 404 | Record introuvable |
| SESSION_NOT_FOUND | 404 | Session introuvable |
| WORKFLOW_ERROR | 500 | Erreur dans le workflow |
| INTERNAL_SERVER_ERROR | 500 | Erreur serveur interne |

Voir [PIPELINE_DOCUMENTATION.md](PIPELINE_DOCUMENTATION.md) pour la liste complète.

## Contribution

Pour mettre à jour la documentation :

1. Modifier les fichiers Markdown dans ce dossier
2. Vérifier que les diagrammes Mermaid sont valides
3. Tester les exemples curl fournis
4. Mettre à jour cette page README si nécessaire

## Liens Utiles

- [README Principal](../README.md)
- [Plans de Développement](../.cursor/plans/)
- [Tests](../tests/)

