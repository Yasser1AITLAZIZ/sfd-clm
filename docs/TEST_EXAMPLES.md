# Exemples de Test - Pipeline OptiClaims

Ce document contient des exemples concrets et prêts à l'emploi pour tester tous les endpoints du pipeline OptiClaims.

## Prérequis

1. Démarrer les services :
```bash
# Terminal 1 - Mock Salesforce
cd mock-salesforce
uvicorn app.main:app --reload --port 8001

# Terminal 2 - Backend MCP
cd backend-mcp
uvicorn app.main:app --reload --port 8000
```

2. Vérifier que les services sont démarrés :
```bash
curl http://localhost:8001/health
curl http://localhost:8000/health
```

## Tests par Endpoint

### 1. Mock Salesforce - Get Record Data

#### Test 1.1 : Record avec facture et photo (001XX000001)

```bash
curl -X POST http://localhost:8001/mock/salesforce/get-record-data \
  -H "Content-Type: application/json" \
  -d '{"record_id": "001XX000001"}'
```

**Résultat attendu** : 2 documents (PDF + JPG), 4 champs à remplir

#### Test 1.2 : Record avec devis (001XX000002)

```bash
curl -X POST http://localhost:8001/mock/salesforce/get-record-data \
  -H "Content-Type: application/json" \
  -d '{"record_id": "001XX000002"}'
```

**Résultat attendu** : 1 document (PDF), 3 champs à remplir

#### Test 1.3 : Record avec rapport expert (001XX000003)

```bash
curl -X POST http://localhost:8001/mock/salesforce/get-record-data \
  -H "Content-Type: application/json" \
  -d '{"record_id": "001XX000003"}'
```

**Résultat attendu** : 2 documents (PDF + ZIP), 4 champs à remplir

#### Test 1.4 : Record inexistant (erreur)

```bash
curl -X POST http://localhost:8001/mock/salesforce/get-record-data \
  -H "Content-Type: application/json" \
  -d '{"record_id": "001XX000999"}'
```

**Résultat attendu** : Erreur 404 - RECORD_NOT_FOUND

#### Test 1.5 : Record ID vide (erreur)

```bash
curl -X POST http://localhost:8001/mock/salesforce/get-record-data \
  -H "Content-Type: application/json" \
  -d '{"record_id": ""}'
```

**Résultat attendu** : Erreur 400 - INVALID_RECORD_ID

### 2. Mock Apex - Send User Request

#### Test 2.1 : Nouvelle session - Extraction complète

```bash
curl -X POST http://localhost:8001/mock/apex/send-user-request \
  -H "Content-Type: application/json" \
  -d '{
    "record_id": "001XX000001",
    "session_id": null,
    "user_request": "Remplis tous les champs manquants"
  }'
```

**Résultat attendu** : Status "sent", request_id généré, timestamp

#### Test 2.2 : Session continue - Question

```bash
curl -X POST http://localhost:8001/mock/apex/send-user-request \
  -H "Content-Type: application/json" \
  -d '{
    "record_id": "001XX000001",
    "session_id": "session-123-456-789",
    "user_request": "Quel est le montant sur la facture ?"
  }'
```

**Résultat attendu** : Status "sent", même session_id

#### Test 2.3 : Session continue - Correction

```bash
curl -X POST http://localhost:8001/mock/apex/send-user-request \
  -H "Content-Type: application/json" \
  -d '{
    "record_id": "001XX000002",
    "session_id": "session-123-456-789",
    "user_request": "Corrige la date, elle semble incorrecte"
  }'
```

**Résultat attendu** : Status "sent"

#### Test 2.4 : Requête vide (erreur)

```bash
curl -X POST http://localhost:8001/mock/apex/send-user-request \
  -H "Content-Type: application/json" \
  -d '{
    "record_id": "001XX000001",
    "session_id": null,
    "user_request": ""
  }'
```

**Résultat attendu** : Erreur 400 - INVALID_USER_REQUEST

### 3. Backend MCP - Receive Request

#### Test 3.1 : Nouvelle session - Initialization Flow

```bash
curl -X POST http://localhost:8000/api/mcp/receive-request \
  -H "Content-Type: application/json" \
  -d '{
    "record_id": "001XX000001",
    "session_id": null,
    "user_message": "Remplis tous les champs manquants"
  }'
```

**Résultat attendu** :
- Status: "success"
- Data.status: "initialization"
- Nouveau session_id généré
- salesforce_data avec documents et champs
- next_step: "preprocessing"

#### Test 3.2 : Session continue - Continuation Flow

```bash
curl -X POST http://localhost:8000/api/mcp/receive-request \
  -H "Content-Type: application/json" \
  -d '{
    "record_id": "001XX000001",
    "session_id": "session-123-456-789",
    "user_message": "Quel est le montant sur la facture ?"
  }'
```

**Résultat attendu** :
- Status: "success"
- Data.status: "continuation"
- Même session_id
- next_step: "prompt_building"
- Pas de salesforce_data

#### Test 3.3 : Extraction avec record différent

```bash
curl -X POST http://localhost:8000/api/mcp/receive-request \
  -H "Content-Type: application/json" \
  -d '{
    "record_id": "001XX000003",
    "session_id": null,
    "user_message": "Extrais toutes les données du rapport expert"
  }'
```

**Résultat attendu** : Initialization avec données du record 001XX000003

#### Test 3.4 : Record ID vide (erreur)

```bash
curl -X POST http://localhost:8000/api/mcp/receive-request \
  -H "Content-Type: application/json" \
  -d '{
    "record_id": "",
    "session_id": null,
    "user_message": "Test"
  }'
```

**Résultat attendu** : Erreur 400 - INVALID_RECORD_ID

#### Test 3.5 : User message vide (erreur)

```bash
curl -X POST http://localhost:8000/api/mcp/receive-request \
  -H "Content-Type: application/json" \
  -d '{
    "record_id": "001XX000001",
    "session_id": null,
    "user_message": ""
  }'
```

**Résultat attendu** : Erreur 400 - INVALID_USER_MESSAGE

### 4. Backend MCP - Request Salesforce Data

#### Test 4.1 : Récupération données internes

```bash
curl -X POST http://localhost:8000/api/mcp/request-salesforce-data \
  -H "Content-Type: application/json" \
  -d '{"record_id": "001XX000001"}'
```

**Résultat attendu** : Même format que Mock Salesforce endpoint

#### Test 4.2 : Record inexistant

```bash
curl -X POST http://localhost:8000/api/mcp/request-salesforce-data \
  -H "Content-Type: application/json" \
  -d '{"record_id": "001XX000999"}'
```

**Résultat attendu** : Erreur 404 - RECORD_NOT_FOUND

### 5. Backend MCP - Task Status

#### Test 5.1 : Tâche complétée (exemple)

```bash
curl -X GET http://localhost:8000/api/task-status/550e8400-e29b-41d4-a716-446655440000
```

**Résultat attendu** : Status de la tâche (pending, processing, completed, failed, ou not_found)

#### Test 5.2 : Tâche inexistante

```bash
curl -X GET http://localhost:8000/api/task-status/00000000-0000-0000-0000-000000000000
```

**Résultat attendu** : Erreur 404 - TASK_NOT_FOUND

## Scénarios de Test Complets

### Scénario A : Workflow Complet - Nouvelle Session

**Étape 1** : Vérifier health check
```bash
curl http://localhost:8000/health
```

**Étape 2** : Créer nouvelle session avec extraction
```bash
curl -X POST http://localhost:8000/api/mcp/receive-request \
  -H "Content-Type: application/json" \
  -d '{
    "record_id": "001XX000001",
    "session_id": null,
    "user_message": "Remplis tous les champs manquants"
  }' | jq '.data.session_id'
```

**Étape 3** : Sauvegarder le session_id (ex: `session-550e8400-e29b-41d4-a716-446655440000`)

**Étape 4** : Vérifier que la session a été créée (via logs ou base de données SQLite)

**Résultat attendu** :
- Session créée avec succès
- Salesforce data récupérée
- Workflow orchestrator a traité la requête

### Scénario B : Workflow Complet - Session Continue

**Étape 1** : Créer session initiale
```bash
SESSION_ID=$(curl -s -X POST http://localhost:8000/api/mcp/receive-request \
  -H "Content-Type: application/json" \
  -d '{
    "record_id": "001XX000001",
    "session_id": null,
    "user_message": "Remplis tous les champs manquants"
  }' | jq -r '.data.session_id')

echo "Session ID: $SESSION_ID"
```

**Étape 2** : Envoyer requête de clarification
```bash
curl -X POST http://localhost:8000/api/mcp/receive-request \
  -H "Content-Type: application/json" \
  -d "{
    \"record_id\": \"001XX000001\",
    \"session_id\": \"$SESSION_ID\",
    \"user_message\": \"Quel est le montant sur la facture ?\"
  }"
```

**Résultat attendu** :
- Status: "continuation"
- Même session_id utilisé
- Pas de récupération Salesforce data
- next_step: "prompt_building"

### Scénario C : Test avec Tous les Records

```bash
# Test avec record 001XX000001
curl -X POST http://localhost:8000/api/mcp/receive-request \
  -H "Content-Type: application/json" \
  -d '{"record_id": "001XX000001", "session_id": null, "user_message": "Test 1"}'

# Test avec record 001XX000002
curl -X POST http://localhost:8000/api/mcp/receive-request \
  -H "Content-Type: application/json" \
  -d '{"record_id": "001XX000002", "session_id": null, "user_message": "Test 2"}'

# Test avec record 001XX000003
curl -X POST http://localhost:8000/api/mcp/receive-request \
  -H "Content-Type: application/json" \
  -d '{"record_id": "001XX000003", "session_id": null, "user_message": "Test 3"}'

# Test avec record 001XX000004
curl -X POST http://localhost:8000/api/mcp/receive-request \
  -H "Content-Type: application/json" \
  -d '{"record_id": "001XX000004", "session_id": null, "user_message": "Test 4"}'

# Test avec record 001XX000005
curl -X POST http://localhost:8000/api/mcp/receive-request \
  -H "Content-Type: application/json" \
  -d '{"record_id": "001XX000005", "session_id": null, "user_message": "Test 5"}'
```

### Scénario D : Test de Robustesse - Erreurs

```bash
# Test 1 : Record ID invalide
curl -X POST http://localhost:8000/api/mcp/receive-request \
  -H "Content-Type: application/json" \
  -d '{"record_id": "", "session_id": null, "user_message": "Test"}'

# Test 2 : User message vide
curl -X POST http://localhost:8000/api/mcp/receive-request \
  -H "Content-Type: application/json" \
  -d '{"record_id": "001XX000001", "session_id": null, "user_message": ""}'

# Test 3 : Record inexistant
curl -X POST http://localhost:8000/api/mcp/receive-request \
  -H "Content-Type: application/json" \
  -d '{"record_id": "001XX000999", "session_id": null, "user_message": "Test"}'

# Test 4 : Session inexistante (continuation)
curl -X POST http://localhost:8000/api/mcp/receive-request \
  -H "Content-Type: application/json" \
  -d '{"record_id": "001XX000001", "session_id": "session-inexistante", "user_message": "Test"}'
```

## Scripts de Test Automatisés

### Script Bash - Test Complet

Créez un fichier `test_pipeline.sh` :

```bash
#!/bin/bash

BASE_URL_MOCK="http://localhost:8001"
BASE_URL_MCP="http://localhost:8000"

echo "=== Test 1: Health Checks ==="
curl -s $BASE_URL_MOCK/health | jq
curl -s $BASE_URL_MCP/health | jq

echo -e "\n=== Test 2: Mock Salesforce - Get Record Data ==="
curl -s -X POST $BASE_URL_MOCK/mock/salesforce/get-record-data \
  -H "Content-Type: application/json" \
  -d '{"record_id": "001XX000001"}' | jq

echo -e "\n=== Test 3: Backend MCP - Receive Request (New Session) ==="
RESPONSE=$(curl -s -X POST $BASE_URL_MCP/api/mcp/receive-request \
  -H "Content-Type: application/json" \
  -d '{
    "record_id": "001XX000001",
    "session_id": null,
    "user_message": "Remplis tous les champs manquants"
  }')

echo $RESPONSE | jq
SESSION_ID=$(echo $RESPONSE | jq -r '.data.session_id')
echo "Session ID créé: $SESSION_ID"

echo -e "\n=== Test 4: Backend MCP - Receive Request (Continuation) ==="
curl -s -X POST $BASE_URL_MCP/api/mcp/receive-request \
  -H "Content-Type: application/json" \
  -d "{
    \"record_id\": \"001XX000001\",
    \"session_id\": \"$SESSION_ID\",
    \"user_message\": \"Quel est le montant sur la facture ?\"
  }" | jq

echo -e "\n=== Tests terminés ==="
```

Rendre le script exécutable :
```bash
chmod +x test_pipeline.sh
./test_pipeline.sh
```

### Script Python - Test Complet

Créez un fichier `test_pipeline.py` :

```python
#!/usr/bin/env python3
"""Script de test complet du pipeline OptiClaims"""
import requests
import json
import sys

BASE_URL_MOCK = "http://localhost:8001"
BASE_URL_MCP = "http://localhost:8000"

def test_health_checks():
    """Test des health checks"""
    print("=== Test 1: Health Checks ===")
    try:
        r = requests.get(f"{BASE_URL_MOCK}/health")
        print(f"Mock Salesforce: {r.status_code} - {r.json()}")
        
        r = requests.get(f"{BASE_URL_MCP}/health")
        print(f"Backend MCP: {r.status_code} - {r.json()}")
    except Exception as e:
        print(f"Erreur health check: {e}")
        sys.exit(1)

def test_get_record_data():
    """Test récupération données mock"""
    print("\n=== Test 2: Mock Salesforce - Get Record Data ===")
    try:
        r = requests.post(
            f"{BASE_URL_MOCK}/mock/salesforce/get-record-data",
            json={"record_id": "001XX000001"}
        )
        print(f"Status: {r.status_code}")
        print(json.dumps(r.json(), indent=2))
        return r.status_code == 200
    except Exception as e:
        print(f"Erreur: {e}")
        return False

def test_receive_request_new_session():
    """Test nouvelle session"""
    print("\n=== Test 3: Backend MCP - Receive Request (New Session) ===")
    try:
        r = requests.post(
            f"{BASE_URL_MCP}/api/mcp/receive-request",
            json={
                "record_id": "001XX000001",
                "session_id": None,
                "user_message": "Remplis tous les champs manquants"
            }
        )
        print(f"Status: {r.status_code}")
        data = r.json()
        print(json.dumps(data, indent=2))
        
        if r.status_code == 200 and data.get("status") == "success":
            session_id = data.get("data", {}).get("session_id")
            print(f"\nSession ID créé: {session_id}")
            return session_id
        return None
    except Exception as e:
        print(f"Erreur: {e}")
        return None

def test_receive_request_continuation(session_id):
    """Test session continue"""
    print("\n=== Test 4: Backend MCP - Receive Request (Continuation) ===")
    try:
        r = requests.post(
            f"{BASE_URL_MCP}/api/mcp/receive-request",
            json={
                "record_id": "001XX000001",
                "session_id": session_id,
                "user_message": "Quel est le montant sur la facture ?"
            }
        )
        print(f"Status: {r.status_code}")
        print(json.dumps(r.json(), indent=2))
        return r.status_code == 200
    except Exception as e:
        print(f"Erreur: {e}")
        return False

if __name__ == "__main__":
    print("Démarrage des tests du pipeline OptiClaims\n")
    
    test_health_checks()
    
    if not test_get_record_data():
        print("Échec test get_record_data")
        sys.exit(1)
    
    session_id = test_receive_request_new_session()
    if not session_id:
        print("Échec test nouvelle session")
        sys.exit(1)
    
    if not test_receive_request_continuation(session_id):
        print("Échec test continuation")
        sys.exit(1)
    
    print("\n=== Tous les tests sont passés avec succès ===")
```

Exécuter :
```bash
python test_pipeline.py
```

## Vérification des Résultats

### Vérifier les Logs

Les services génèrent des logs structurés JSON. Vérifiez les logs pour :
- Validation des inputs
- Création de sessions
- Appels aux services
- Erreurs éventuelles

### Vérifier SQLite (Sessions)

Les sessions sont stockées dans SQLite. Vous pouvez vérifier les sessions :
```bash
# Depuis le répertoire backend-mcp
sqlite3 data/sessions.db
> SELECT session_id, record_id, created_at FROM sessions;
> SELECT * FROM sessions WHERE session_id = '<session_id>';
```

### Vérifier les Réponses

Toutes les réponses doivent avoir :
- Status code HTTP approprié (200, 400, 404, 500, etc.)
- Format JSON valide
- Structure conforme aux schémas définis
- Codes d'erreur cohérents en cas d'échec

## Notes

- Utilisez `jq` pour formater les réponses JSON : `curl ... | jq`
- Les UUIDs de session et request_id sont générés automatiquement
- Les timestamps sont au format ISO 8601
- Les erreurs suivent un format standardisé avec code, message, et details

