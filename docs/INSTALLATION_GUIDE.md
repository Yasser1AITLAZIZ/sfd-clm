# Guide d'Installation Complet - OptiClaims

Ce guide vous accompagne étape par étape pour installer et configurer l'environnement de développement OptiClaims.

## Table des Matières

1. [Prérequis](#prérequis)
2. [Installation Automatique](#installation-automatique)
3. [Installation Manuelle](#installation-manuelle)
4. [Configuration](#configuration)
5. [Vérification](#vérification)
6. [Dépannage](#dépannage)

## Prérequis

### Python 3.11+

#### Vérification

**Linux / Mac :**
```bash
python3 --version
```

**Windows :**
```powershell
python --version
```

#### Installation

- **Linux (Ubuntu/Debian)** :
  ```bash
  sudo apt update
  sudo apt install python3.11 python3.11-venv python3-pip
  ```

- **Mac** :
  ```bash
  brew install python@3.11
  ```

- **Windows** :
  Téléchargez depuis [python.org](https://www.python.org/downloads/)
  - ✅ Cochez "Add Python to PATH" lors de l'installation

### Session Storage (SQLite)

Le stockage de session utilise SQLite, qui est inclus dans Python. Aucune installation supplémentaire n'est requise. Le répertoire `data/` sera créé automatiquement au premier démarrage.

### Git (Optionnel)

Pour cloner le dépôt :

```bash
git clone <repository-url>
cd sfd-clm
```

## Installation Automatique

### Linux / Mac

1. **Rendre les scripts exécutables** :
   ```bash
   chmod +x setup_venv.sh verify_setup.sh
   ```

2. **Exécuter le script d'installation** :
   ```bash
   ./setup_venv.sh
   ```

Le script va :
- ✅ Vérifier Python 3.11+
- ✅ Créer les environnements virtuels pour chaque service
- ✅ Installer toutes les dépendances
- ✅ Préparer le répertoire SQLite pour le stockage de session

### Windows (PowerShell)

1. **Ouvrir PowerShell en tant qu'administrateur** (recommandé)

2. **Autoriser l'exécution de scripts** (si nécessaire) :
   ```powershell
   Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
   ```

3. **Exécuter le script d'installation** :
   ```powershell
   .\setup_venv.ps1
   ```

## Installation Manuelle

Si vous préférez installer manuellement ou si les scripts automatiques échouent :

### 1. Backend MCP

```bash
# Naviguer vers le service
cd backend-mcp

# Créer l'environnement virtuel
python3 -m venv venv  # Linux/Mac
# ou
python -m venv venv  # Windows

# Activer l'environnement
source venv/bin/activate  # Linux/Mac
# ou
venv\Scripts\activate  # Windows

# Mettre à jour pip
pip install --upgrade pip

# Installer les dépendances
pip install -r requirements.txt

# Désactiver l'environnement
deactivate
```

### 2. Backend LangGraph

```bash
cd backend-langgraph
python3 -m venv venv  # Linux/Mac
# ou
python -m venv venv  # Windows

source venv/bin/activate  # Linux/Mac
# ou
venv\Scripts\activate  # Windows

pip install --upgrade pip
pip install -r requirements.txt
deactivate
```

### 3. Mock Salesforce

```bash
cd mock-salesforce
python3 -m venv venv  # Linux/Mac
# ou
python -m venv venv  # Windows

source venv/bin/activate  # Linux/Mac
# ou
venv\Scripts\activate  # Windows

pip install --upgrade pip
pip install -r requirements.txt
deactivate
```

## Configuration

### Variables d'Environnement

Créez des fichiers `.env` dans chaque service si nécessaire :

#### backend-mcp/.env

```env
# Application
LOG_LEVEL=INFO
LOG_FORMAT=console  # "console" pour logs lisibles, "json" pour logs structurés

# Server
HOST=0.0.0.0
PORT=8000

# External Services
MOCK_SALESFORCE_URL=http://localhost:8001
SALESFORCE_REQUEST_TIMEOUT=5.0

# Session Storage (SQLite)
SESSION_DB_PATH=data/sessions.db
SESSION_TTL_SECONDS=86400

# LangGraph
LANGGRAPH_URL=http://localhost:8002
LANGGRAPH_API_KEY=
LANGGRAPH_TIMEOUT=30.0
```

#### backend-langgraph/.env

```env
# Application
LOG_LEVEL=INFO
LOG_FORMAT=console

# Server
HOST=0.0.0.0
PORT=8002

# API Keys (si nécessaire)
# OPENAI_API_KEY=your_key_here
# ANTHROPIC_API_KEY=your_key_here
```

## Vérification

### Script de Vérification Automatique

#### Linux / Mac

```bash
./verify_setup.sh
```

#### Windows

```powershell
.\verify_setup.ps1
```

### Vérification Manuelle

1. **Vérifier les environnements virtuels** :
   ```bash
   ls backend-mcp/venv/        # Linux/Mac
   dir backend-mcp\venv\        # Windows
   ```

2. **Vérifier les dépendances** :
   ```bash
   cd backend-mcp
   source venv/bin/activate  # Linux/Mac
   # ou
   venv\Scripts\activate  # Windows
   pip list
   deactivate
   ```

3. **Tester les imports** :
   ```bash
   cd backend-mcp
   source venv/bin/activate
   python -c "from app.main import app; print('✅ Import successful')"
   deactivate
   ```

## Dépannage

### Problème : Python non trouvé

**Symptôme** : `python: command not found` ou `python3: command not found`

**Solution** :
- Vérifiez que Python est installé : `python --version`
- Ajoutez Python au PATH (Windows)
- Utilisez `python3` au lieu de `python` (Linux/Mac)

### Problème : Erreur lors de la création du venv

**Symptôme** : `Error: Command 'python -m venv' failed`

**Solution** :
- Installez le module venv : `sudo apt install python3-venv` (Linux)
- Vérifiez que Python 3.11+ est installé
- Utilisez `python3 -m venv` au lieu de `python -m venv`

### Problème : Erreur d'installation des dépendances

**Symptôme** : `ERROR: Could not find a version that satisfies the requirement`

**Solution** :
- Mettez à jour pip : `pip install --upgrade pip`
- Vérifiez votre connexion Internet
- Essayez avec `--no-cache-dir` : `pip install -r requirements.txt --no-cache-dir`
- Vérifiez que vous êtes dans le bon venv

### Problème : Erreur de base de données SQLite

**Symptôme** : `Failed to initialize SQLite database`

**Solution** :
- Vérifiez que le répertoire `backend-mcp/data/` existe et est accessible en écriture
- Vérifiez le chemin de la base de données dans `.env` (`SESSION_DB_PATH`)
- Le répertoire `data/` sera créé automatiquement si nécessaire

### Problème : Port déjà utilisé

**Symptôme** : `Address already in use` ou `Port 8000 is already in use`

**Solution** :
- Trouvez le processus utilisant le port :
  ```bash
  # Linux/Mac
  lsof -i :8000
  # Windows
  netstat -ano | findstr :8000
  ```
- Arrêtez le processus ou changez le port dans `.env`

### Problème : Erreurs d'import après installation

**Symptôme** : `ModuleNotFoundError: No module named 'app'`

**Solution** :
- Assurez-vous d'être dans le bon répertoire
- Vérifiez que le venv est activé : `which python` devrait pointer vers `venv/bin/python`
- Réinstallez les dépendances : `pip install -r requirements.txt --force-reinstall`

### Problème : Scripts PowerShell bloqués (Windows)

**Symptôme** : `cannot be loaded because running scripts is disabled on this system`

**Solution** :
```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

## Prochaines Étapes

Une fois l'installation terminée :

1. ✅ Vérifiez l'installation : `./verify_setup.sh` ou `.\verify_setup.ps1`
2. 📖 Lisez le [README.md](../README.md) pour démarrer les services
3. 🧪 Testez avec `test-data/test_pipeline.py`
4. 📚 Consultez la [documentation du pipeline](PIPELINE_DOCUMENTATION.md)

## Support

Pour plus d'aide :
- Consultez les logs : `test-data/results/logs/`
- Vérifiez la [documentation complète](PIPELINE_DOCUMENTATION.md)
- Ouvrez une issue sur le dépôt

