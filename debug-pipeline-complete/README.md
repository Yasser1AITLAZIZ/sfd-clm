# Complete Pipeline Debug Script

Ce script exécute tous les steps du pipeline de bout en bout et enregistre les outputs de chaque étape.

## Utilisation

### Prérequis

1. Activer l'environnement virtuel `backend-mcp` :
```powershell
cd backend-mcp
.\venv\Scripts\Activate.ps1
cd ..
```

2. S'assurer que les services Docker sont en cours d'exécution :
```powershell
docker-compose ps
```

Si les services ne sont pas en cours d'exécution :
```powershell
docker-compose up -d
```

### Exécution

```powershell
python debug-pipeline-complete/run_complete_pipeline.py
```

## Structure des Outputs

Le script génère les fichiers suivants dans le dossier `debug-pipeline-complete/` :

### Fichiers par Step

- `step1_output.json` - Output de Step 1 (Mock Salesforce Retrieval)
- `step2_output.json` - Output de Step 2 (Salesforce Client Fetch)
- `step3_output.json` - Output de Step 3 (Preprocessing Pipeline)
- `step4_output.json` - Output de Step 4 (Prompt Building)
- `step5_output.json` - Output de Step 5 (Prompt Optimization)
- `step6_output.json` - Output de Step 6 (MCP Formatting)
- `step7_output.json` - Output de Step 7 (MCP Sending)

### Fichiers de Résumé

- `pipeline_summary_YYYYMMDD_HHMMSS.json` - Résumé de l'exécution avec métriques clés
- `complete_results_YYYYMMDD_HHMMSS.json` - Résultats complets avec tous les détails
- `complete_pipeline_YYYYMMDD_HHMMSS.log` - Log complet de l'exécution

## Structure du Résumé

Le fichier `pipeline_summary_*.json` contient :

```json
{
  "timestamp": "2025-12-31T23:00:00",
  "test_record_id": "001XX000001",
  "overall_status": "success",
  "steps_completed": 7,
  "steps_failed": 0,
  "steps_warning": 0,
  "steps": {
    "step1": {
      "step_number": 1,
      "status": "success",
      "documents_count": 1,
      "fields_count": 13
    },
    "step2": {
      "step_number": 2,
      "status": "success",
      "fields_to_fill_count": 13
    },
    ...
    "step7": {
      "step_number": 7,
      "status": "success",
      "extracted_data_count": 8,
      "confidence_scores_count": 8,
      "quality_score": 0.96
    }
  }
}
```

## Interprétation des Résultats

### Status des Steps

- **success** : Le step s'est exécuté avec succès
- **warning** : Le step s'est exécuté mais avec des avertissements (ex: service non disponible)
- **error** : Le step a échoué

### Métriques Clés

- **Step 1** : Nombre de documents et champs chargés
- **Step 2** : Nombre de champs convertis
- **Step 3** : Documents traités et champs enrichis
- **Step 4** : Longueur du prompt construit
- **Step 5** : Longueur originale vs optimisée, score de qualité
- **Step 6** : Message MCP formaté avec documents et champs
- **Step 7** : **Nombre de champs extraits** (métrique principale), scores de confiance, qualité

## Dépannage

### Step 1 échoue
- Vérifier que `test-data/fields/001XX000001_fields.json` existe
- Vérifier que `test-data/documents/` contient des fichiers PDF

### Step 2 échoue
- Vérifier que le service Mock Salesforce est en cours d'exécution (`http://localhost:8001/health`)
- Vérifier que le volume `test-data` est monté dans Docker

### Step 7 échoue
- Vérifier que le service LangGraph est en cours d'exécution (`http://localhost:8002/health`)
- Vérifier les logs LangGraph pour les erreurs de traitement

### Aucune donnée extraite dans Step 7
- Vérifier que les steps précédents ont réussi
- Vérifier les logs LangGraph pour les erreurs de mapping
- Utiliser `diagnose_mcp_extraction.py` pour diagnostiquer le problème

