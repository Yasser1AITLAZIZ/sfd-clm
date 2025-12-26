# Documentation OptiClaims

Ce dossier contient la documentation complète et à jour du pipeline OptiClaims.

## 📚 Fichiers de Documentation

### [API_REFERENCE.md](API_REFERENCE.md) ⭐ **NOUVEAU**

**Référence complète de toutes les APIs** avec spécifications détaillées :

- ✅ **Spécifications input/output** pour toutes les APIs
- ✅ **Exemples de requêtes/réponses** en JSON
- ✅ **Codes d'erreur** complets
- ✅ **Formats de données** détaillés
- ✅ **Exemples cURL** prêts à l'emploi

**À consulter pour** : Intégration API, développement, tests

### [PIPELINE_FLOW.md](PIPELINE_FLOW.md) ⭐ **NOUVEAU**

**Flux visuels et détaillés du pipeline** :

- ✅ **Diagrammes de flux** Mermaid complets
- ✅ **Séquences détaillées** étape par étape
- ✅ **Workflow Orchestrator** - 8 étapes complètes
- ✅ **Flux Initialization vs Continuation**
- ✅ **Gestion des erreurs** et monitoring
- ✅ **Performance** et optimisations

**À consulter pour** : Comprendre le fonctionnement, architecture, debugging

### [ARCHITECTURE.md](ARCHITECTURE.md)

**Architecture complète du projet** :

- Vue d'ensemble des services
- Flux de données principaux
- Workflow Orchestrator détaillé
- Gestion des sessions
- Formats de données

**À consulter pour** : Architecture système, design patterns

### [INSTALLATION_GUIDE.md](INSTALLATION_GUIDE.md)

**Guide d'installation complet** :

- Prérequis
- Installation manuelle des venvs
- Scripts automatisés (Bash/PowerShell)
- Configuration
- Dépannage

**À consulter pour** : Installation, configuration initiale

### [PIPELINE_DOCUMENTATION.md](PIPELINE_DOCUMENTATION.md)

**Documentation historique du pipeline** (à jour) :

- État d'avancement du projet
- Documentation des endpoints (référencez API_REFERENCE.md pour les détails)
- Données mock disponibles
- Scénarios de test

**À consulter pour** : Vue d'ensemble historique, données mock

### [TEST_EXAMPLES.md](TEST_EXAMPLES.md)

**Exemples pratiques de tests** :

- Tests par endpoint
- Scénarios de test complets
- Scripts automatisés (Bash/Python)
- Vérification des résultats

**À consulter pour** : Tests, validation, exemples pratiques


## 🚀 Navigation Rapide

### Pour intégrer les APIs
→ **[API_REFERENCE.md](API_REFERENCE.md)** - Spécifications complètes input/output

### Pour comprendre le flux du pipeline
→ **[PIPELINE_FLOW.md](PIPELINE_FLOW.md)** - Diagrammes et séquences détaillées

### Pour installer le projet
→ **[INSTALLATION_GUIDE.md](INSTALLATION_GUIDE.md)** - Guide complet d'installation

### Pour comprendre l'architecture
→ **[ARCHITECTURE.md](ARCHITECTURE.md)** - Architecture système complète

### Pour tester le pipeline
→ **[TEST_EXAMPLES.md](TEST_EXAMPLES.md)** - Exemples et scripts de test

### Pour les données mock
→ **[PIPELINE_DOCUMENTATION.md](PIPELINE_DOCUMENTATION.md)** - Section "Données Mock Disponibles"

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

