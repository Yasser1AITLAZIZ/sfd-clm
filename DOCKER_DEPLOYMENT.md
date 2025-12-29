# Guide de Déploiement Docker Compose

Ce guide explique comment déployer et tester les services du projet SFD-CLM en utilisant Docker Compose.

## Prérequis

- Docker Desktop (Windows/Mac) ou Docker Engine (Linux)
- docker-compose (inclus avec Docker Desktop)
- Python 3.11+ (pour exécuter les tests)

## Structure des Services

Le projet contient trois services principaux :

1. **mock-salesforce** (port 8001) : Service mock pour simuler l'API Salesforce
2. **backend-mcp** (port 8000) : Service principal de traitement MCP
3. **backend-langgraph** (port 8002) : Service LangGraph pour le traitement LLM

## Démarrage Rapide

### 1. Démarrer tous les services

```bash
docker-compose up -d --build
```

Cette commande va :
- Construire les images Docker pour chaque service
- Démarrer tous les services en arrière-plan
- Configurer le réseau interne entre les services

### 2. Vérifier que les services sont prêts

```bash
# Vérifier les logs
docker-compose logs -f

# Vérifier le statut
docker-compose ps

# Tester les endpoints de santé
curl http://localhost:8001/health  # mock-salesforce
curl http://localhost:8000/health  # backend-mcp
curl http://localhost:8002/health  # backend-langgraph
```

### 3. Exécuter les tests de bout en bout

**Windows :**
```powershell
.\test-data\run_pipeline_test_docker.ps1
```

**Linux/Mac :**
```bash
chmod +x test-data/run_pipeline_test_docker.sh
./test-data/run_pipeline_test_docker.sh
```

Le script va :
- Vérifier que Docker est en cours d'exécution
- Démarrer les services si nécessaire
- Attendre que tous les services soient prêts
- Exécuter le test de pipeline
- Proposer d'arrêter les services après le test

## Commandes Utiles

### Gestion des Services

```bash
# Démarrer les services
docker-compose up -d

# Arrêter les services
docker-compose down

# Redémarrer un service spécifique
docker-compose restart backend-mcp

# Voir les logs d'un service
docker-compose logs -f backend-mcp

# Voir les logs de tous les services
docker-compose logs -f

# Reconstruire les images
docker-compose build --no-cache

# Arrêter et supprimer les volumes (⚠️ supprime les données)
docker-compose down -v
```

### Accès aux Conteneurs

```bash
# Exécuter une commande dans un conteneur
docker-compose exec backend-mcp bash
docker-compose exec mock-salesforce bash
docker-compose exec backend-langgraph bash

# Voir les processus dans un conteneur
docker-compose exec backend-mcp ps aux
```

### Debugging

```bash
# Voir les logs en temps réel
docker-compose logs -f --tail=100

# Voir les logs d'un service spécifique
docker-compose logs -f backend-mcp

# Vérifier la configuration
docker-compose config

# Voir l'utilisation des ressources
docker stats
```

## Configuration

### Variables d'Environnement

Les variables d'environnement peuvent être définies dans :
- Le fichier `docker-compose.yml`
- Un fichier `.env` à la racine du projet
- Directement dans la ligne de commande

### Volumes

Les volumes Docker sont utilisés pour :
- **backend_mcp_data** : Base de données SQLite des sessions
- **mock_salesforce_data** : Données de test du mock Salesforce

Les volumes persistent même après l'arrêt des conteneurs.

### Réseau

Tous les services sont sur le réseau `sfd-clm-network` et peuvent communiquer entre eux via leurs noms de service :
- `http://mock-salesforce:8000`
- `http://backend-mcp:8000`
- `http://backend-langgraph:8002`

## Tests

### Test Automatique

Le script `run_pipeline_test_docker.ps1` (Windows) ou `run_pipeline_test_docker.sh` (Linux/Mac) exécute automatiquement :
1. Vérification de Docker
2. Démarrage des services si nécessaire
3. Attente de la disponibilité des services
4. Exécution du test de pipeline
5. Option d'arrêt des services

### Test Manuel

```bash
# 1. Démarrer les services
docker-compose up -d

# 2. Attendre que les services soient prêts
sleep 10

# 3. Exécuter le test Python
python test-data/test_pipeline.py

# 4. Vérifier les résultats
ls -la test-data/results/
```

## Dépannage

### Les services ne démarrent pas

1. Vérifier que Docker est en cours d'exécution
2. Vérifier les logs : `docker-compose logs`
3. Vérifier les ports : `netstat -an | grep 8000`
4. Reconstruire les images : `docker-compose build --no-cache`

### Les services ne communiquent pas entre eux

1. Vérifier le réseau : `docker network ls`
2. Vérifier que les services sont sur le même réseau
3. Tester la connectivité : `docker-compose exec backend-mcp ping mock-salesforce`

### Erreurs de permissions

Sur Linux, vous pourriez avoir besoin de :
```bash
sudo chown -R $USER:$USER test-data/results/
```

### Nettoyer complètement

```bash
# Arrêter et supprimer tout
docker-compose down -v

# Supprimer les images
docker-compose rm -f

# Nettoyer les images non utilisées
docker system prune -a
```

## Architecture

```
┌─────────────────────────────────────────────────┐
│              Docker Network                     │
│           (sfd-clm-network)                     │
│                                                 │
│  ┌──────────────┐    ┌──────────────┐          │
│  │ mock-        │    │ backend-     │          │
│  │ salesforce   │◄───┤ mcp          │          │
│  │ :8000        │    │ :8000        │          │
│  └──────────────┘    └──────┬───────┘          │
│                             │                   │
│                             ▼                   │
│                      ┌──────────────┐          │
│                      │ backend-     │          │
│                      │ langgraph    │          │
│                      │ :8002        │          │
│                      └──────────────┘          │
│                                                 │
└─────────────────────────────────────────────────┘
         │                    │
         │                    │
    Port 8001           Port 8000
    Port 8002
```

## Production

Pour un déploiement en production, considérez :

1. **Sécurité** :
   - Utiliser des secrets Docker au lieu de variables d'environnement
   - Configurer HTTPS/TLS
   - Limiter les ports exposés

2. **Performance** :
   - Utiliser des images optimisées (multi-stage builds)
   - Configurer des limites de ressources
   - Utiliser un reverse proxy (nginx, traefik)

3. **Monitoring** :
   - Intégrer des outils de monitoring (Prometheus, Grafana)
   - Configurer des alertes
   - Centraliser les logs (ELK, Loki)

4. **Haute Disponibilité** :
   - Utiliser Docker Swarm ou Kubernetes
   - Configurer des health checks
   - Implémenter des stratégies de redémarrage

## Support

Pour plus d'informations, consultez :
- [README.md](README.md) - Documentation principale
- [docs/](docs/) - Documentation détaillée
- [BUG_ANALYSIS.md](BUG_ANALYSIS.md) - Analyse des bugs connus

