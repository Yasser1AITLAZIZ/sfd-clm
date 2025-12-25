# Système de test pipeline end-to-end

Ce dossier contient les fichiers nécessaires pour tester le pipeline complet de traitement de documents.

## Structure

- `documents/` - Placez vos fichiers PDF de test ici
- `fields/` - Placez le JSON des champs Salesforce ici
- `results/` - Résultats des tests et logs

## Utilisation rapide

1. Placez vos PDFs dans `documents/`
2. Placez `fields.json` dans `fields/`
3. Exécutez le script de test :
   - **Linux/Mac/WSL** : `./run_pipeline_test.sh`
   - **Windows** : `.\run_pipeline_test.ps1`

## Format du JSON des champs

Le fichier `fields/fields.json` doit suivre exactement le format de `final_form_fields_page_infor_des_circons.json` :

```json
{
  "fields": [
    {
      "label": "Nom du champ",
      "apiName": null,
      "type": "text|picklist|radio|number|textarea",
      "required": true,
      "possibleValues": [],
      "defaultValue": null
    }
  ]
}
```

## Scripts disponibles

- `run_pipeline_test.sh` / `run_pipeline_test.ps1` - Démarre les services et exécute le test complet
- `start_services.sh` / `start_services.ps1` - Démarre uniquement les services
- `stop_services.sh` / `stop_services.ps1` - Arrête tous les services
- `view_logs.sh` / `view_logs.ps1` - Visualise et filtre les logs

## Résultats

Les résultats sont sauvegardés dans `results/` :
- `results/test_results_{timestamp}.json` - Résultats du test
- `results/logs/` - Logs de chaque service

## Debugging

Pour suivre les logs en temps réel ou filtrer par workflow_id :

```bash
# Voir les logs d'un service
cat results/logs/backend-mcp.log | jq '.'

# Filtrer par workflow_id
cat results/logs/*.log | jq 'select(.workflow_id == "xxx")'

# Filtrer les erreurs
cat results/logs/*.log | jq 'select(.level == "ERROR")'
```

