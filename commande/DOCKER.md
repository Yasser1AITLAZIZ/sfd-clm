# Commandes Docker

## Description

Alternative au démarrage manuel des services avec docker-compose.

## Prérequis

- Docker installé
- Docker Compose installé
- Fichier `docker-compose.yml` à la racine du projet

## Commandes Principales

### Démarrer tous les services

```bash
docker-compose up
```

Démarrer en arrière-plan (détaché) :
```bash
docker-compose up -d
```

### Arrêter tous les services

```bash
docker-compose down
```

Arrêter et supprimer les volumes :
```bash
docker-compose down -v
```

### Démarrer un service spécifique

```bash
docker-compose up mock-salesforce
docker-compose up backend-mcp
docker-compose up backend-langgraph
```

### Arrêter un service spécifique

```bash
docker-compose stop mock-salesforce
docker-compose stop backend-mcp
docker-compose stop backend-langgraph
```

## Voir les Logs

### Tous les services
```bash
docker-compose logs -f
```

### Un service spécifique
```bash
docker-compose logs -f mock-salesforce
docker-compose logs -f backend-mcp
docker-compose logs -f backend-langgraph
```

## Reconstruire les Images

Si vous modifiez les Dockerfiles ou requirements.txt :

```bash
docker-compose build
```

Reconstruire sans cache :
```bash
docker-compose build --no-cache
```

## Vérifier l'État des Services

```bash
docker-compose ps
```

## Redémarrer un Service

```bash
docker-compose restart mock-salesforce
docker-compose restart backend-mcp
docker-compose restart backend-langgraph
```

## Avantages vs Démarrage Manuel

### Avantages
- ✅ Isolation des environnements
- ✅ Pas besoin d'activer les venv
- ✅ Configuration centralisée
- ✅ Facile à partager avec l'équipe
- ✅ Gestion automatique des dépendances

### Inconvénients
- ❌ Plus lent au démarrage (build des images)
- ❌ Consommation mémoire plus élevée
- ❌ Moins de contrôle sur l'environnement Python
- ❌ Debugging plus complexe

## Services Disponibles

1. **mock-salesforce** : Port 8001
2. **backend-mcp** : Port 8000
3. **backend-langgraph** : Port 8002

## Ordre de Démarrage Recommandé

Les services sont configurés avec `depends_on` dans docker-compose.yml, donc l'ordre est géré automatiquement :

1. mock-salesforce (doit être démarré en premier)
2. backend-langgraph (peut démarrer en parallèle)
3. backend-mcp (attend que les autres soient prêts)

## Configuration Docker

Le fichier `docker-compose.yml` contient :
- Configuration des ports
- Variables d'environnement
- Volumes pour le code source
- Health checks
- Réseau Docker interne

