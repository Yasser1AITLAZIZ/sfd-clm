# Commandes - Mock Salesforce

## Description

Service mock simulant Salesforce pour le développement et les tests.

- **Port** : 8001
- **URL** : http://localhost:8001
- **Health Check** : http://localhost:8001/health

## Prérequis

- Python 3.10.9
- Environnement virtuel activé
- Dépendances installées (`pip install -r requirements.txt`)

## Commandes de Démarrage

### Démarrage Manuel

#### Windows (PowerShell)
```powershell
cd mock-salesforce
.\venv\Scripts\activate
uvicorn app.main:app --reload --port 8001
```

#### Linux/Mac
```bash
cd mock-salesforce
source venv/bin/activate
uvicorn app.main:app --reload --port 8001
```

### Démarrage avec Docker

```bash
docker-compose up mock-salesforce
```

Ou depuis la racine du projet :
```bash
docker-compose up -d mock-salesforce
```

## Vérification

### Health Check
```bash
curl http://localhost:8001/health
```

Ou dans un navigateur : http://localhost:8001/health

### Test Endpoint Principal
```bash
curl -X POST http://localhost:8001/mock/salesforce/get-record-data \
  -H "Content-Type: application/json" \
  -d '{"record_id": "001XX000001"}'
```

## Endpoints Principaux

- `POST /mock/salesforce/get-record-data` : Récupère les données mock pour un record_id
- `POST /mock/apex/send-user-request` : Simule l'envoi d'une requête utilisateur
- `GET /health` : Health check

## Arrêt du Service

### Si démarré manuellement
- Appuyer sur `Ctrl+C` dans le terminal

### Si démarré avec Docker
```bash
docker-compose stop mock-salesforce
```

Ou pour arrêter et supprimer le conteneur :
```bash
docker-compose down mock-salesforce
```

## Logs

Les logs s'affichent dans la console où le service a été démarré.

Pour Docker :
```bash
docker-compose logs -f mock-salesforce
```

