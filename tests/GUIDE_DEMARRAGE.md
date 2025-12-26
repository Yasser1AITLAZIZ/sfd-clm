# Guide de Démarrage - Services de Test

## 🪟 Pour Windows

### Option 1 : Script automatique (Recommandé)

1. **Ouvrir PowerShell ou CMD** dans le dossier du projet
   ```powershell
   cd C:\Users\YasserAITLAZIZ\sfd-clm
   ```

2. **Vérifier que Python est installé** (SQLite est inclus dans Python)
   ```powershell
   python --version
   ```
   - SQLite est inclus dans Python, aucune installation supplémentaire requise ✅
   - Le répertoire `backend-mcp/data/` sera créé automatiquement au premier démarrage

3. **Lancer le script de démarrage**
   ```powershell
   tests\start_services.bat
   ```
   
   Ou double-cliquer sur `tests\start_services.bat` dans l'explorateur Windows

4. **Vérifier que les services démarrent**
   - Deux nouvelles fenêtres CMD s'ouvriront :
     - Une pour Mock Salesforce (port 8001)
     - Une pour Backend MCP (port 8000)
   - Vous devriez voir des messages de démarrage dans chaque fenêtre

5. **Tester que les services fonctionnent**
   ```powershell
   # Dans un nouveau terminal
   curl http://localhost:8001/health
   curl http://localhost:8000/health
   ```

### Option 2 : Démarrage manuel (Pour débogage)

#### Terminal 1 : Mock Salesforce
```powershell
cd C:\Users\YasserAITLAZIZ\sfd-clm\mock-salesforce
uvicorn app.main:app --port 8001 --reload
```

#### Terminal 2 : Backend MCP
```powershell
cd C:\Users\YasserAITLAZIZ\sfd-clm\backend-mcp
uvicorn app.main:app --port 8000 --reload
```

#### Terminal 3 : (Optionnel) Monitoring SQLite
Le répertoire `backend-mcp/data/` sera créé automatiquement au premier démarrage.

---

## 🐧 Pour Linux/Mac (avec script .sh)

### Étape 1 : Ouvrir un terminal
```bash
cd ~/sfd-clm
# ou
cd /chemin/vers/sfd-clm
```

### Étape 2 : Rendre le script exécutable
```bash
chmod +x tests/start_services.sh
```

### Étape 3 : Vérifier les prérequis

**3.1. Vérifier que Python 3.11+ est installé**
```bash
python3 --version
```

**3.3. Vérifier que les dépendances sont installées**
```bash
# Backend MCP
cd backend-mcp
pip install -r requirements.txt
cd ..

# Mock Salesforce
cd mock-salesforce
pip install -r requirements.txt
cd ..
```

### Étape 4 : Lancer le script
```bash
./tests/start_services.sh
```

### Étape 5 : Vérifier le résultat

Le script devrait afficher :
```
==========================================
Starting OptiClaims Services for Testing
==========================================

Checking SQLite...
✅ SQLite is ready (included in Python)

Starting Mock Salesforce service on port 8001...
✅ Mock Salesforce service started (PID: 12345)

Starting Backend MCP service on port 8000...
✅ Backend MCP service started (PID: 12346)

==========================================
All services are running!
==========================================

Mock Salesforce: http://localhost:8001
Backend MCP: http://localhost:8000

Ready for testing! Run: python tests/test_pipeline_simple.py
```

### Étape 6 : Tester les services

Dans un nouveau terminal :
```bash
# Test Mock Salesforce
curl http://localhost:8001/health

# Test Backend MCP
curl http://localhost:8000/health
```

Les deux devraient retourner un JSON avec `"status": "healthy"`

---

## 🔧 Dépannage

### Problème : "Permission denied" (Linux/Mac)
```bash
chmod +x tests/start_services.sh
```

### Problème : "Erreur de base de données SQLite"
- Vérifier que le répertoire `backend-mcp/data/` existe et est accessible en écriture
- Vérifier le chemin de la base de données dans la configuration (`SESSION_DB_PATH`)
- Le répertoire `data/` sera créé automatiquement si nécessaire

### Problème : "Port already in use"
```bash
# Linux/Mac - Trouver le processus utilisant le port
lsof -i :8000
lsof -i :8001

# Tuer le processus
kill -9 <PID>

# Windows - Trouver le processus
netstat -ano | findstr :8000
netstat -ano | findstr :8001

# Tuer le processus (remplacer PID)
taskkill /PID <PID> /F
```

### Problème : "Module not found"
```bash
# Installer les dépendances
cd backend-mcp
pip install -r requirements.txt
cd ../mock-salesforce
pip install -r requirements.txt
```

### Problème : Services ne démarrent pas
1. Vérifier les logs dans les terminaux
2. Vérifier que les ports 8000 et 8001 sont libres
3. Vérifier que SQLite est accessible (le répertoire backend-mcp/data/ sera créé automatiquement)
4. Vérifier les variables d'environnement si configurées

---

## ✅ Vérification finale

Une fois les services démarrés, vous devriez pouvoir :

1. **Accéder aux docs API** :
   - Mock Salesforce : http://localhost:8001/docs
   - Backend MCP : http://localhost:8000/docs

2. **Tester avec curl** :
   ```bash
   # Health check
   curl http://localhost:8001/health
   curl http://localhost:8000/health
   
   # Test endpoint
   curl -X POST http://localhost:8001/mock/salesforce/get-record-data \
     -H "Content-Type: application/json" \
     -d '{"record_id": "001XXXX"}'
   ```

3. **Lancer les tests** :
   ```bash
   python tests/test_pipeline_simple.py
   ```

---

## 🛑 Arrêter les services

### Windows
- Fermer les fenêtres CMD ouvertes par le script
- Ou utiliser le gestionnaire de tâches pour tuer les processus Python

### Linux/Mac
```bash
# Utiliser le script d'arrêt
./tests/stop_services.sh

# Ou manuellement
kill <PID_MOCK_SF> <PID_MCP>

# Ou trouver et tuer par port
lsof -ti:8000 | xargs kill -9
lsof -ti:8001 | xargs kill -9
```

---

## 📝 Notes importantes

- **Ne fermez pas les terminaux** où les services tournent
- Les services utilisent `--reload` donc ils redémarrent automatiquement si vous modifiez le code
- SQLite est inclus dans Python, aucune action supplémentaire requise
- Les ports 8000 et 8001 doivent être libres

---

## 🚀 Prochaines étapes

Une fois les services démarrés :

1. **Test rapide** :
   ```bash
   python tests/test_pipeline_simple.py
   ```

2. **Test complet** :
   ```bash
   python tests/test_pipeline_e2e.py
   ```

3. **Test des composants** :
   ```bash
   python tests/test_workflow_components.py
   ```

