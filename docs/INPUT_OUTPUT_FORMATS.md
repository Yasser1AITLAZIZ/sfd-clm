# Formats Input/Output - OptiClaims

Documentation complète des formats de données d'entrée et de sortie du système OptiClaims.

## Vue d'Ensemble

Le système OptiClaims utilise une architecture **Form JSON As-Is** où les champs du formulaire sont envoyés tels quels à travers le pipeline, avec seulement une normalisation minimale.

## Format Input : Salesforce → Mock Salesforce

### Requête

**Endpoint** : `POST /mock/salesforce/get-record-data`

**Body** :
```json
{
  "record_id": "001XX000001"
}
```

### Réponse

```json
{
  "status": "success",
  "data": {
    "record_id": "001XX000001",
    "record_type": "Claim",
    "documents": [
      {
        "document_id": "doc_123",
        "name": "facture.pdf",
        "url": "https://example.com/documents/facture.pdf",
        "type": "application/pdf",
        "indexed": true
      }
    ],
    "fields_to_fill": [
      {
        "label": "Evènement déclencheur de sinistre",
        "apiName": null,
        "type": "picklist",
        "required": true,
        "possibleValues": [
          "Accident",
          "Assistance",
          "Bris de glace",
          "Incendie",
          "Évènement Catastrophe/ climatique & naturel"
        ],
        "defaultValue": "Accident"
      },
      {
        "label": "Nombre de véhicules impliqués",
        "apiName": null,
        "type": "number",
        "required": false,
        "possibleValues": [],
        "defaultValue": null
      }
    ]
  }
}
```

## Format Normalisé : Après Preprocessing

### Structure PreprocessedDataSchema

```json
{
  "record_id": "001XX000001",
  "record_type": "Claim",
  "processed_documents": [
    {
      "document_id": "doc_123",
      "name": "facture.pdf",
      "url": "https://example.com/documents/facture.pdf",
      "type": "application/pdf",
      "indexed": true,
      "metadata": {
        "filename": "facture.pdf",
        "size": 102400,
        "mime_type": "application/pdf",
        "pages_count": 3
      },
      "processed": true
    }
  ],
  "salesforce_data": {
    "record_id": "001XX000001",
    "record_type": "Claim",
    "documents": [
      {
        "document_id": "doc_123",
        "name": "facture.pdf",
        "url": "https://example.com/documents/facture.pdf",
        "type": "application/pdf",
        "indexed": true
      }
    ],
    "fields_to_fill": [
      {
        "label": "Evènement déclencheur de sinistre",
        "apiName": null,
        "type": "picklist",
        "required": true,
        "possibleValues": [
          "Accident",
          "Assistance",
          "Bris de glace",
          "Incendie",
          "Évènement Catastrophe/ climatique & naturel"
        ],
        "defaultValue": null,
        "dataValue_target_AI": null
      },
      {
        "label": "Nombre de véhicules impliqués",
        "apiName": null,
        "type": "number",
        "required": false,
        "possibleValues": [],
        "defaultValue": null,
        "dataValue_target_AI": null
      }
    ]
  },
  "context_summary": {
    "record_type": "Claim",
    "objective": "Extraire et remplir les champs manquants pour un Claim",
    "documents_available": [
      {
        "document_id": "doc_123",
        "name": "facture.pdf",
        "type": "application/pdf"
      }
    ],
    "fields_to_extract": [
      {
        "label": "Evènement déclencheur de sinistre",
        "type": "picklist",
        "required": true,
        "apiName": null
      }
    ],
    "business_rules": [
      "Tous les champs requis doivent être remplis",
      "Les montants doivent être positifs",
      "Les dates doivent être au format ISO (YYYY-MM-DD)",
      "Les données doivent être cohérentes entre documents"
    ]
  },
  "validation_results": {
    "passed": true,
    "errors": [],
    "warnings": []
  },
  "metrics": {
    "processing_time_seconds": 1.2,
    "data_size_bytes": 51200,
    "documents_count": 1,
    "fields_count": 2
  }
}
```

### Points Clés

- **Nested Structure** : `preprocessed_data.salesforce_data.fields_to_fill` contient les champs normalisés
- **Normalization** : 
  - `dataValue_target_AI: null` ajouté si absent
  - `defaultValue: null` forcé pour tous les champs
- **Preservation** : Tous les autres champs préservés (label, type, possibleValues, etc.)

## Format Prompt : Avec form_json Embeded

### Prompt Template

```jinja2
# Contexte
Type de record: {{ record_type }}
Objectif: {{ objective }}

# Documents disponibles
{% for doc in documents %}
- {{ doc.name }} ({{ doc.type }})
{% endfor %}

# Form Fields (JSON)
{{ form_json }}

# Requête utilisateur
{{ user_request }}

# Instructions
{{ instructions }}
```

### Prompt Rendu (Exemple)

```
# Contexte
Type de record: Claim
Objectif: Extraire et remplir les champs manquants pour un Claim

# Documents disponibles
- facture.pdf (application/pdf)

# Form Fields (JSON)
[
  {
    "label": "Evènement déclencheur de sinistre",
    "apiName": null,
    "type": "picklist",
    "required": true,
    "possibleValues": [
      "Accident",
      "Assistance",
      "Bris de glace",
      "Incendie",
      "Évènement Catastrophe/ climatique & naturel"
    ],
    "defaultValue": null,
    "dataValue_target_AI": null
  },
  {
    "label": "Nombre de véhicules impliqués",
    "apiName": null,
    "type": "number",
    "required": false,
    "possibleValues": [],
    "defaultValue": null,
    "dataValue_target_AI": null
  }
]

# Requête utilisateur
Remplis tous les champs manquants

# Instructions
Analysez les documents et remplissez les champs du formulaire...
```

## Format Langgraph Request

### Requête vers Langgraph

**Endpoint** : `POST /api/langgraph/process-mcp-request`

**Body** :
```json
{
  "record_id": "001XX000001",
  "session_id": "session-550e8400-e29b-41d4-a716-446655440000",
  "user_request": "Full prompt text with form_json embedded...",
  "documents": [
    {
      "id": "doc_123",
      "type": "application/pdf",
      "pages": [
        {
          "page_number": 1,
          "image_b64": "JVBERi0xLjQKJeLjz9MKMy...",
          "image_mime": "application/pdf"
        }
      ]
    }
  ],
  "form_json": [
    {
      "label": "Evènement déclencheur de sinistre",
      "apiName": null,
      "type": "picklist",
      "required": true,
      "possibleValues": [
        "Accident",
        "Assistance",
        "Bris de glace",
        "Incendie",
        "Évènement Catastrophe/ climatique & naturel"
      ],
      "defaultValue": null,
      "dataValue_target_AI": null
    },
    {
      "label": "Nombre de véhicules impliqués",
      "apiName": null,
      "type": "number",
      "required": false,
      "possibleValues": [],
      "defaultValue": null,
      "dataValue_target_AI": null
    }
  ]
}
```

## Format Langgraph Response

### Réponse de Langgraph

```json
{
  "status": "success",
  "data": {
    "filled_form_json": [
      {
        "label": "Evènement déclencheur de sinistre",
        "apiName": null,
        "type": "picklist",
        "required": true,
        "possibleValues": [
          "Accident",
          "Assistance",
          "Bris de glace",
          "Incendie",
          "Évènement Catastrophe/ climatique & naturel"
        ],
        "defaultValue": null,
        "dataValue_target_AI": "Accident",
        "confidence": 0.98
      },
      {
        "label": "Nombre de véhicules impliqués",
        "apiName": null,
        "type": "number",
        "required": false,
        "possibleValues": [],
        "defaultValue": null,
        "dataValue_target_AI": "2",
        "confidence": 0.95
      }
    ],
    "confidence_scores": {
      "Evènement déclencheur de sinistre": 0.98,
      "Nombre de véhicules impliqués": 0.95
    },
    "processing_time": 2.5,
    "ocr_text_length": 5000,
    "text_blocks_count": 25,
    "metrics": {
      "tokens_used": 1500,
      "llm_calls": 3
    }
  }
}
```

### Cas : Information Non Trouvée (Golden Rule)

Si l'information n'est pas trouvée dans le texte OCR, `dataValue_target_AI` est rempli avec `"non disponible"` :

```json
{
  "filled_form_json": [
    {
      "label": "Evènement déclencheur de sinistre",
      "type": "picklist",
      "required": true,
      "possibleValues": ["Accident", "Assistance", "Bris de glace"],
      "defaultValue": null,
      "dataValue_target_AI": "non disponible",
      "confidence": 0.0
    }
  ]
}
```

## Format Output : Backend MCP → Salesforce

### Réponse Workflow Complète

```json
{
  "status": "completed",
  "workflow_id": "workflow-550e8400-e29b-41d4-a716-446655440000",
  "current_step": null,
  "steps_completed": [
    "validation_routing",
    "preprocessing",
    "prompt_building",
    "prompt_optimization",
    "mcp_formatting",
    "mcp_sending",
    "response_handling"
  ],
  "filled_form_json": [
    {
      "label": "Evènement déclencheur de sinistre",
      "apiName": null,
      "type": "picklist",
      "required": true,
      "possibleValues": [
        "Accident",
        "Assistance",
        "Bris de glace",
        "Incendie",
        "Évènement Catastrophe/ climatique & naturel"
      ],
      "defaultValue": null,
      "dataValue_target_AI": "Accident",
      "confidence": 0.98
    },
    {
      "label": "Nombre de véhicules impliqués",
      "apiName": null,
      "type": "number",
      "required": false,
      "possibleValues": [],
      "defaultValue": null,
      "dataValue_target_AI": "2",
      "confidence": 0.95
    }
  ],
  "confidence_scores": {
    "Evènement déclencheur de sinistre": 0.98,
    "Nombre de véhicules impliqués": 0.95
  },
  "data": {
    "routing": {
      "status": "initialization",
      "session_id": "session-550e8400-e29b-41d4-a716-446655440000",
      "salesforce_data": {...}
    },
    "preprocessing": {
      "preprocessed_data": {...}
    },
    "prompt_building": {
      "prompt": "...",
      "scenario_type": "initialization"
    },
    "prompt_optimization": {
      "optimized_prompt": "...",
      "quality_score": 0.95
    },
    "mcp_formatting": {
      "mcp_message": {...}
    },
    "mcp_sending": {
      "mcp_response": {
        "filled_form_json": [...],
        "confidence_scores": {...}
      }
    },
    "response_handling": {
      "filled_form_json": [...],
      "confidence_scores": {...},
      "final_status": "success"
    }
  },
  "errors": [],
  "started_at": "2024-01-15T10:30:00Z",
  "completed_at": "2024-01-15T10:30:45Z"
}
```

## Schéma de Données

### SalesforceFormFieldSchema (Input)

```python
{
    "label": str,                    # Ex: "Evènement déclencheur de sinistre"
    "apiName": Optional[str],         # Ex: null ou "Event__c"
    "type": str,                     # Ex: "picklist", "text", "number", "textarea", "radio"
    "required": bool,                # Ex: true
    "possibleValues": List[str],     # Ex: ["Accident", "Assistance", ...] (vide pour text/number)
    "defaultValue": Any             # Ex: "Accident" ou null (sera forcé à null)
}
```

### Normalized Form JSON (After Preprocessing)

```python
{
    "label": str,
    "apiName": Optional[str],
    "type": str,
    "required": bool,
    "possibleValues": List[str],
    "defaultValue": null,            # Toujours null après normalisation
    "dataValue_target_AI": null     # Ajouté si absent
}
```

### Filled Form JSON (Output)

```python
{
    "label": str,
    "apiName": Optional[str],
    "type": str,
    "required": bool,
    "possibleValues": List[str],
    "defaultValue": null,
    "dataValue_target_AI": str | "non disponible",  # Rempli par Mapping Manager
    "confidence": float              # 0.0-1.0, ajouté par Mapping Manager
}
```

## Exemples Complets

### Exemple 1 : Champ Picklist avec Valeur Trouvée

**Input** :
```json
{
  "label": "Evènement déclencheur de sinistre",
  "type": "picklist",
  "required": true,
  "possibleValues": ["Accident", "Assistance", "Bris de glace"],
  "defaultValue": "Accident"
}
```

**After Normalization** :
```json
{
  "label": "Evènement déclencheur de sinistre",
  "type": "picklist",
  "required": true,
  "possibleValues": ["Accident", "Assistance", "Bris de glace"],
  "defaultValue": null,
  "dataValue_target_AI": null
}
```

**Output (Value Found)** :
```json
{
  "label": "Evènement déclencheur de sinistre",
  "type": "picklist",
  "required": true,
  "possibleValues": ["Accident", "Assistance", "Bris de glace"],
  "defaultValue": null,
  "dataValue_target_AI": "Accident",
  "confidence": 0.98
}
```

**Output (Value Not Found - Golden Rule)** :
```json
{
  "label": "Evènement déclencheur de sinistre",
  "type": "picklist",
  "required": true,
  "possibleValues": ["Accident", "Assistance", "Bris de glace"],
  "defaultValue": null,
  "dataValue_target_AI": "non disponible",
  "confidence": 0.0
}
```

### Exemple 2 : Champ Text avec Valeur Extraite

**Input** :
```json
{
  "label": "Commentaire",
  "type": "textarea",
  "required": false,
  "possibleValues": [],
  "defaultValue": null
}
```

**After Normalization** :
```json
{
  "label": "Commentaire",
  "type": "textarea",
  "required": false,
  "possibleValues": [],
  "defaultValue": null,
  "dataValue_target_AI": null
}
```

**Output (Value Found)** :
```json
{
  "label": "Commentaire",
  "type": "textarea",
  "required": false,
  "possibleValues": [],
  "defaultValue": null,
  "dataValue_target_AI": "Le véhicule a été endommagé lors d'une collision",
  "confidence": 0.92
}
```

**Output (Value Not Found - Golden Rule)** :
```json
{
  "label": "Commentaire",
  "type": "textarea",
  "required": false,
  "possibleValues": [],
  "defaultValue": null,
  "dataValue_target_AI": "non disponible",
  "confidence": 0.0
}
```

### Exemple 3 : Champ Number

**Input** :
```json
{
  "label": "Nombre de véhicules impliqués",
  "type": "number",
  "required": false,
  "possibleValues": [],
  "defaultValue": null
}
```

**Output (Value Found)** :
```json
{
  "label": "Nombre de véhicules impliqués",
  "type": "number",
  "required": false,
  "possibleValues": [],
  "defaultValue": null,
  "dataValue_target_AI": "2",
  "confidence": 0.95
}
```

## Règles de Transformation

### Normalization Rules

1. **dataValue_target_AI** :
   - Si absent → Ajouter `"dataValue_target_AI": null`
   - Si présent → Toujours mettre à `null` (sera rempli plus tard)

2. **defaultValue** :
   - Toujours mettre à `null` (même si valeur présente dans input)
   - Raison : Éviter le biais dans l'extraction

3. **Autres champs** :
   - Préserver exactement tels quels
   - Pas de transformation de label, type, possibleValues, etc.

### Mapping Rules (Golden Rule)

1. **Si information trouvée dans OCR** :
   - Pour picklist/radio : Choisir valeur exacte parmi `possibleValues`
   - Pour text/number/textarea : Extraire directement depuis OCR
   - Remplir `dataValue_target_AI` avec la valeur
   - Ajouter `confidence` (0.0-1.0)

2. **Si information NON trouvée dans OCR** :
   - Remplir `dataValue_target_AI` avec `"non disponible"`
   - Ne JAMAIS utiliser `null` ou chaîne vide
   - Mettre `confidence` à `0.0`

3. **Structure de réponse** :
   - Retourner le MÊME JSON avec la même structure
   - Ne changer QUE `dataValue_target_AI` et `confidence`
   - Préserver tous les autres champs

## Validation

### Input Validation

- `record_id` : Requis, non vide
- `fields_to_fill` : Liste non vide (peut être vide mais log warning)
- `documents` : Liste (peut être vide mais log warning)
- Chaque champ doit avoir `label` et `type`

### Output Validation

- `filled_form_json` : Même longueur que input `form_json`
- Chaque champ doit avoir `dataValue_target_AI` (non null)
- `confidence` : Entre 0.0 et 1.0
- Structure identique à input (même ordre, mêmes champs)

## Erreurs et Cas Limites

### Cas 1 : Champs Vides

**Input** : `fields_to_fill: []`

**Comportement** :
- Log warning
- Continue avec liste vide
- Retourne `filled_form_json: []`

### Cas 2 : Documents Vides

**Input** : `documents: []`

**Comportement** :
- Log warning
- Continue avec liste vide
- Mapping Manager appliquera Golden Rule : `"non disponible"` pour tous les champs

### Cas 3 : Record ID Manquant

**Input** : `record_id: ""` ou `null`

**Comportement** :
- Default à `"unknown"` gracieusement
- Continue le workflow
- Log warning

### Cas 4 : OCR Échoue

**Comportement** :
- Mapping Manager applique Golden Rule
- Tous les champs → `dataValue_target_AI: "non disponible"`
- `confidence: 0.0` pour tous
- Retourne `filled_form_json` avec valeurs "non disponible"

## Comparaison Avant/Après

### Avant (Architecture Complexe)

```python
# Multiple transformations
SalesforceFormFieldSchema
  → FieldToFillResponseSchema (conversion avec perte d'accents)
    → EnrichedFieldSchema (enrichissement)
      → FieldsDictionarySchema (prioritisation)
        → fields_dictionary: Dict[str, Any] (perte de structure)
```

**Problèmes** :
- Perte d'informations (accents, possibleValues)
- Structure complexe et difficile à suivre
- Conversion multiple avec risque d'erreur

### Après (Architecture Simplifiée)

```python
# Simple normalization
SalesforceFormFieldSchema
  → Normalized Form JSON (ajout dataValue_target_AI, defaultValue: null)
    → form_json: List[Dict] (structure préservée)
      → filled_form_json: List[Dict] (même structure, valeurs remplies)
```

**Avantages** :
- Préservation totale des informations
- Structure simple et claire
- Transformation minimale
- Même structure input/output

