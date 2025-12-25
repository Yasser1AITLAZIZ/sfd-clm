# Flux du Pipeline OptiClaims

Documentation visuelle et détaillée du flux de données dans le pipeline OptiClaims.

## Vue d'Ensemble

Le pipeline OptiClaims traite les requêtes Salesforce pour extraire automatiquement des données depuis des documents en utilisant l'IA générative.

```mermaid
flowchart TB
    Start([Salesforce Apex Controller]) -->|POST /api/mcp/receive-request| MCP[Backend MCP Service]
    MCP -->|Validate & Route| Route{Session existe?}
    
    Route -->|Non| Init[Initialization Flow]
    Route -->|Oui| Cont[Continuation Flow]
    
    Init -->|POST /mock/salesforce/get-record-data| MSF[Mock Salesforce Service]
    MSF -->|Documents + Fields| MCP
    
    Init --> Preprocess[Preprocessing Pipeline]
    Cont --> PromptBuild[Prompt Building]
    
    Preprocess --> PromptBuild
    PromptBuild --> Optimize[Prompt Optimization]
    Optimize --> Format[MCP Message Formatting]
    Format -->|POST /api/langgraph/process-mcp-request| LG[Backend LangGraph Service]
    
    LG --> OCR[OCR Processing]
    OCR --> Mapping[Field Mapping]
    Mapping --> Extract[Data Extraction]
    Extract -->|Extracted Data| MCP
    
    MCP -->|Store/Update| Redis[(Redis Session Storage)]
    MCP -->|Workflow Result| End([Return to Salesforce])
    
    style Start fill:#e1f5ff
    style MCP fill:#fff4e1
    style MSF fill:#e1ffe1
    style LG fill:#ffe1e1
    style Redis fill:#f0e1ff
    style End fill:#e1f5ff
```

## Flux Détaillé : Initialization

### 1. Réception de la Requête

```mermaid
sequenceDiagram
    participant SF as Salesforce
    participant MCP as Backend MCP
    participant Validator as Request Validator
    
    SF->>MCP: POST /api/mcp/receive-request<br/>{record_id, session_id: null, user_message}
    MCP->>Validator: Validate Input
    Validator-->>MCP: Valid
    MCP->>MCP: Check Session (null = new)
    MCP->>MCP: Route to Initialization
```

**Input** :
```json
{
  "record_id": "001XX000001",
  "session_id": null,
  "user_message": "Remplis tous les champs manquants"
}
```

### 2. Récupération des Données Salesforce

```mermaid
sequenceDiagram
    participant MCP as Backend MCP
    participant MSF as Mock Salesforce
    participant Redis as Redis Storage
    
    MCP->>MSF: POST /mock/salesforce/get-record-data<br/>{record_id}
    MSF-->>MCP: {documents, fields}
    MCP->>MCP: Generate Session ID
    MCP->>Redis: Create Session
    Redis-->>MCP: Session Created
```

**Output de Mock Salesforce** :
```json
{
  "status": "success",
  "data": {
    "record_id": "001XX000001",
    "record_type": "Claim",
    "documents": [...],
    "fields": [...]
  }
}
```

### 3. Preprocessing

```mermaid
flowchart LR
    A[Salesforce Data] --> B[Document Preprocessor]
    A --> C[Fields Preprocessor]
    B --> D[Processed Documents]
    C --> E[Fields Dictionary]
    D --> F[Preprocessed Data]
    E --> F
    F --> G[Context Summary]
```

**Étapes** :
1. **Document Preprocessing** :
   - Validation des documents
   - Extraction des métadonnées
   - Calcul du score de qualité
   - Préparation pour OCR

2. **Fields Preprocessing** :
   - Enrichissement des champs
   - Classification (vide/prérempli)
   - Priorisation
   - Génération du dictionnaire

3. **Context Summary** :
   - Résumé du contexte métier
   - Règles de validation
   - Objectif d'extraction

### 4. Prompt Building

```mermaid
flowchart TD
    A[Preprocessed Data] --> B[Prompt Template Engine]
    B --> C{Scenario Type}
    C -->|Initialization| D[Initialization Template]
    C -->|Continuation| E[Continuation Template]
    C -->|Clarification| F[Clarification Template]
    D --> G[Prompt Builder]
    E --> G
    F --> G
    G --> H[Final Prompt]
```

**Types de prompts** :
- **Initialization** : Première extraction complète
- **Extraction** : Extraction de champs spécifiques
- **Clarification** : Demande de précision
- **Validation** : Vérification des données
- **Continuation** : Suite de conversation

### 5. Prompt Optimization

```mermaid
flowchart LR
    A[Original Prompt] --> B[Token Analysis]
    B --> C[Optimization Rules]
    C --> D[Token Reduction]
    C --> E[Clarity Improvement]
    D --> F[Optimized Prompt]
    E --> F
    F --> G[Quality Score]
```

**Optimisations appliquées** :
- Réduction de tokens
- Amélioration de la clarté
- Structuration optimale
- Estimation des coûts

### 6. MCP Formatting & Sending

```mermaid
sequenceDiagram
    participant MCP as Backend MCP
    participant Formatter as MCP Formatter
    participant LG as Backend LangGraph
    
    MCP->>Formatter: Format MCP Message
    Formatter->>Formatter: Build Message Structure
    Formatter-->>MCP: MCP Message
    MCP->>LG: POST /api/langgraph/process-mcp-request
    LG-->>MCP: Extracted Data + Confidence Scores
```

**MCP Message Structure** :
```json
{
  "message_id": "msg-...",
  "prompt": "Optimized prompt...",
  "context": {
    "documents": [...],
    "fields": [...],
    "session_id": "..."
  },
  "metadata": {
    "record_id": "...",
    "record_type": "Claim",
    "timestamp": "..."
  }
}
```

### 7. LangGraph Processing

```mermaid
flowchart TD
    A[MCP Request] --> B[OCR Manager]
    B --> C[OCR Processing]
    C --> D[Text Blocks Extraction]
    D --> E[Mapping Manager]
    E --> F[Field Mapping]
    F --> G[Data Extraction]
    G --> H[Validation]
    H --> I[Response Formatting]
    I --> J[Return to MCP]
```

**Étapes LangGraph** :
1. **OCR Processing** : Extraction de texte depuis images
2. **Text Blocks** : Détection de blocs structurés
3. **Field Mapping** : Association champs → texte
4. **Data Extraction** : Extraction des valeurs
5. **Validation** : Vérification de la qualité
6. **Response** : Formatage de la réponse

### 8. Response Handling

```mermaid
flowchart LR
    A[LangGraph Response] --> B[Extract Data]
    B --> C[Update Session]
    C --> D[Store in Redis]
    D --> E[Build Workflow Result]
    E --> F[Return to Salesforce]
```

**Workflow Result Structure** :
```json
{
  "status": "completed",
  "workflow_id": "...",
  "data": {
    "response_handling": {
      "extracted_data": {...},
      "confidence_scores": {...},
      "final_status": "success"
    }
  }
}
```

## Flux Détaillé : Continuation

### 1. Réception de la Requête (Session Existante)

```mermaid
sequenceDiagram
    participant SF as Salesforce
    participant MCP as Backend MCP
    participant Redis as Redis Storage
    
    SF->>MCP: POST /api/mcp/receive-request<br/>{record_id, session_id, user_message}
    MCP->>Redis: Get Session
    Redis-->>MCP: Session Data
    MCP->>MCP: Route to Continuation
```

**Input** :
```json
{
  "record_id": "001XX000001",
  "session_id": "session-550e8400-...",
  "user_message": "Quel est le montant sur la facture ?"
}
```

### 2. Continuation Flow

```mermaid
flowchart TD
    A[Get Session from Redis] --> B[Load Context]
    B --> C[Add User Message to History]
    C --> D[Prompt Building]
    D --> E[Prompt Optimization]
    E --> F[MCP Formatting]
    F --> G[Send to LangGraph]
    G --> H[Process Response]
    H --> I[Update Session]
    I --> J[Return Result]
```

**Différences avec Initialization** :
- Pas de récupération Salesforce data
- Utilisation du contexte de session
- Ajout à l'historique de conversation
- Prompt de type "continuation" ou "clarification"

## Workflow Orchestrator - Étapes Complètes

```mermaid
flowchart TD
    Start([Receive Request]) --> Step1[Step 1: Validation & Routing]
    Step1 -->|New Session| Step2[Step 2: Fetch Salesforce Data]
    Step1 -->|Existing Session| Step4
    Step2 --> Step3[Step 3: Preprocessing]
    Step3 --> Step4[Step 4: Prompt Building]
    Step4 --> Step5[Step 5: Prompt Optimization]
    Step5 --> Step6[Step 6: MCP Formatting]
    Step6 --> Step7[Step 7: MCP Sending]
    Step7 --> Step8[Step 8: Response Handling]
    Step8 --> End([Return Workflow Result])
    
    style Step1 fill:#e1f5ff
    style Step2 fill:#fff4e1
    style Step3 fill:#e1ffe1
    style Step4 fill:#e1ffe1
    style Step5 fill:#e1ffe1
    style Step6 fill:#e1ffe1
    style Step7 fill:#ffe1e1
    style Step8 fill:#f0e1ff
```

### Détails des Étapes

#### Step 1: Validation & Routing
- Validation des inputs
- Vérification de la session
- Routage vers Initialization ou Continuation

#### Step 2: Fetch Salesforce Data (Initialization uniquement)
- Appel à Mock Salesforce
- Récupération documents + champs
- Création de session

#### Step 3: Preprocessing
- Preprocessing des documents
- Preprocessing des champs
- Génération du contexte

#### Step 4: Prompt Building
- Sélection du template
- Construction du prompt
- Ajout du contexte

#### Step 5: Prompt Optimization
- Analyse des tokens
- Optimisation
- Calcul du score de qualité

#### Step 6: MCP Formatting
- Formatage du message MCP
- Ajout des métadonnées
- Génération du message_id

#### Step 7: MCP Sending
- Envoi à Backend LangGraph
- Attente de la réponse
- Gestion des erreurs

#### Step 8: Response Handling
- Extraction des données
- Mise à jour de la session
- Construction du résultat final

## Gestion des Erreurs

```mermaid
flowchart TD
    A[Error Occurred] --> B{Error Type}
    B -->|Validation| C[Return 400 Bad Request]
    B -->|Not Found| D[Return 404 Not Found]
    B -->|Workflow| E[Log Error]
    E --> F[Add to errors array]
    F --> G[Continue or Fail]
    G -->|Continue| H[Next Step]
    G -->|Fail| I[Return 500 with details]
    
    style C fill:#ffe1e1
    style D fill:#ffe1e1
    style I fill:#ffe1e1
```

**Stratégie d'erreur** :
- Erreurs de validation : Arrêt immédiat (400)
- Erreurs de workflow : Log + Ajout à `errors` array
- Erreurs critiques : Arrêt du workflow (500)
- Erreurs non-critiques : Continuation avec warning

## Logging et Monitoring

```mermaid
flowchart LR
    A[Workflow Step] --> B[Log Progress]
    B --> C[Log Timing]
    C --> D[Log Results]
    D --> E[Console Output]
    D --> F[JSON Logs]
    
    style B fill:#e1ffe1
    style C fill:#e1ffe1
    style D fill:#e1ffe1
```

**Types de logs** :
- **Progress** : `[PROGRESS 1/7] Starting Validation & Routing`
- **Timing** : `[TIMING] Step 1 completed (took 0.45s)`
- **Results** : Données extraites, scores de confiance
- **Errors** : Détails des erreurs avec contexte

## Performance et Optimisations

### Temps d'Exécution Typiques

| Étape | Temps Moyen | Description |
|-------|-------------|-------------|
| Validation & Routing | 0.1s | Validation rapide |
| Fetch Salesforce Data | 0.2s | Appel HTTP |
| Preprocessing | 1.0s | Traitement documents + champs |
| Prompt Building | 0.5s | Construction du prompt |
| Prompt Optimization | 0.3s | Optimisation |
| MCP Formatting | 0.1s | Formatage |
| MCP Sending | 10-30s | Traitement LangGraph (OCR + Extraction) |
| Response Handling | 0.2s | Mise à jour session |
| **Total** | **12-32s** | Workflow complet |

### Optimisations

1. **Caching** : Sessions Redis pour éviter re-fetch Salesforce
2. **Async Processing** : Tâches asynchrones pour longues opérations
3. **Prompt Optimization** : Réduction des tokens pour coûts
4. **Parallel Processing** : Traitement parallèle des documents (futur)

## Exemples de Flux Complets

### Exemple 1 : Nouvelle Session - Extraction Complète

```
1. Salesforce → MCP : {record_id: "001XX000001", session_id: null, user_message: "Remplis tous les champs"}
2. MCP → Mock SF : Get record data
3. Mock SF → MCP : Documents + Fields
4. MCP : Preprocessing
5. MCP : Prompt Building (Initialization)
6. MCP : Prompt Optimization
7. MCP → LangGraph : MCP Message
8. LangGraph : OCR + Extraction
9. LangGraph → MCP : Extracted Data
10. MCP : Update Session
11. MCP → Salesforce : Workflow Result
```

### Exemple 2 : Session Continue - Clarification

```
1. Salesforce → MCP : {record_id: "001XX000001", session_id: "session-...", user_message: "Quel est le montant ?"}
2. MCP : Get Session from Redis
3. MCP : Prompt Building (Continuation)
4. MCP : Prompt Optimization
5. MCP → LangGraph : MCP Message
6. LangGraph : Process with context
7. LangGraph → MCP : Response
8. MCP : Update Session
9. MCP → Salesforce : Workflow Result
```

