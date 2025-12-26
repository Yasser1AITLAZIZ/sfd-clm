# Index de la Documentation OptiClaims

Guide de navigation rapide dans toute la documentation du projet.

## 🎯 Par Objectif

### Je veux intégrer les APIs
→ **[API_REFERENCE.md](API_REFERENCE.md)**  
Spécifications complètes input/output pour toutes les APIs avec exemples JSON et cURL.

### Je veux comprendre le flux du pipeline
→ **[PIPELINE_FLOW.md](PIPELINE_FLOW.md)**  
Diagrammes de flux détaillés, séquences étape par étape, workflow orchestrator complet.

### Je veux installer le projet
→ **[INSTALLATION_GUIDE.md](INSTALLATION_GUIDE.md)**  
Guide complet d'installation avec scripts automatisés (Bash/PowerShell).

### Je veux comprendre l'architecture
→ **[ARCHITECTURE.md](ARCHITECTURE.md)**  
Architecture système complète, services, flux de données, gestion des sessions.

### Je veux tester le pipeline
→ **[TEST_EXAMPLES.md](TEST_EXAMPLES.md)**  
Exemples pratiques, scripts de test, scénarios complets.

### Je veux voir l'état du projet
→ **[PIPELINE_DOCUMENTATION.md](PIPELINE_DOCUMENTATION.md)**  
État d'avancement, données mock disponibles, vue d'ensemble historique.

## 📋 Par Type de Documentation

### Référence API
- **[API_REFERENCE.md](API_REFERENCE.md)** - Spécifications complètes de toutes les APIs

### Architecture & Flux
- **[ARCHITECTURE.md](ARCHITECTURE.md)** - Architecture système
- **[PIPELINE_FLOW.md](PIPELINE_FLOW.md)** - Flux détaillés avec diagrammes

### Installation & Configuration
- **[INSTALLATION_GUIDE.md](INSTALLATION_GUIDE.md)** - Installation complète

### Tests & Exemples
- **[TEST_EXAMPLES.md](TEST_EXAMPLES.md)** - Exemples de tests
- **[PIPELINE_DOCUMENTATION.md](PIPELINE_DOCUMENTATION.md)** - Données mock et scénarios

## 🗺️ Par Service

### Mock Salesforce (Port 8001)
- **API** : [API_REFERENCE.md](API_REFERENCE.md#mock-salesforce-service)
- **Tests** : [TEST_EXAMPLES.md](TEST_EXAMPLES.md#1-mock-salesforce---get-record-data)
- **Flux** : [PIPELINE_FLOW.md](PIPELINE_FLOW.md#2-récupération-des-données-salesforce)

### Backend MCP (Port 8000)
- **API** : [API_REFERENCE.md](API_REFERENCE.md#backend-mcp-service)
- **Tests** : [TEST_EXAMPLES.md](TEST_EXAMPLES.md#3-backend-mcp---receive-request)
- **Flux** : [PIPELINE_FLOW.md](PIPELINE_FLOW.md#flux-détaillé-initialization)
- **Architecture** : [ARCHITECTURE.md](ARCHITECTURE.md#backend-mcp-service)

### Backend LangGraph (Port 8002)
- **API** : [API_REFERENCE.md](API_REFERENCE.md#backend-langgraph-service)
- **Flux** : [PIPELINE_FLOW.md](PIPELINE_FLOW.md#7-langgraph-processing)
- **Architecture** : [ARCHITECTURE.md](ARCHITECTURE.md#backend-langgraph-service)

## 📊 Diagrammes Disponibles

### Dans PIPELINE_FLOW.md
- ✅ Vue d'ensemble du pipeline
- ✅ Flux Initialization complet
- ✅ Flux Continuation complet
- ✅ Workflow Orchestrator - 8 étapes
- ✅ Gestion des erreurs
- ✅ Logging et monitoring

### Dans ARCHITECTURE.md
- ✅ Architecture des services
- ✅ Flux de données principal
- ✅ Workflow Orchestrator détaillé
- ✅ Gestion des sessions

## 🔍 Recherche Rapide

### Codes d'Erreur
→ [API_REFERENCE.md](API_REFERENCE.md#codes-derreur)

### Formats de Données
→ [API_REFERENCE.md](API_REFERENCE.md#formats-de-données)

### Données Mock Disponibles
→ [PIPELINE_DOCUMENTATION.md](PIPELINE_DOCUMENTATION.md#données-mock-disponibles)

### Scripts d'Installation
→ [INSTALLATION_GUIDE.md](INSTALLATION_GUIDE.md#installation-automatisée)

### Exemples cURL
→ [API_REFERENCE.md](API_REFERENCE.md) (dans chaque section d'endpoint)

### Performance et Temps d'Exécution
→ [PIPELINE_FLOW.md](PIPELINE_FLOW.md#performance-et-optimisations)

## 🚀 Quick Start

1. **Installation** : [INSTALLATION_GUIDE.md](INSTALLATION_GUIDE.md)
2. **Comprendre le flux** : [PIPELINE_FLOW.md](PIPELINE_FLOW.md)
3. **Tester une API** : [API_REFERENCE.md](API_REFERENCE.md)
4. **Exemples de test** : [TEST_EXAMPLES.md](TEST_EXAMPLES.md)

## 📝 Structure de la Documentation

```
docs/
├── INDEX.md                    ← Vous êtes ici
├── README.md                    ← Vue d'ensemble de la documentation
├── API_REFERENCE.md             ← Référence complète des APIs ⭐
├── PIPELINE_FLOW.md             ← Flux détaillés avec diagrammes ⭐
├── ARCHITECTURE.md              ← Architecture système
├── INSTALLATION_GUIDE.md        ← Guide d'installation
├── PIPELINE_DOCUMENTATION.md   ← Documentation historique
└── TEST_EXAMPLES.md             ← Exemples de tests
```

## ✅ Documentation à Jour

Toute la documentation a été révisée et mise à jour pour refléter l'état actuel du projet :

- ✅ Toutes les APIs sont documentées avec input/output complets
- ✅ Tous les diagrammes de flux sont à jour
- ✅ L'état d'avancement reflète la réalité (tous les services sont implémentés)
- ✅ Les exemples de code sont fonctionnels
- ✅ Les formats de données correspondent au code actuel

## 🔗 Liens Utiles

- [README Principal](../README.md)
- [Tests](../tests/)
- [Test Data](../test-data/)

