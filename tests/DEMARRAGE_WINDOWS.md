# Guide de Démarrage - Windows

## 🎯 Démarrage Rapide (3 étapes)

### Étape 1 : Vérifier SQLite

SQLite est inclus dans Python, aucune installation supplémentaire n'est requise.

**Vérifier que Python est installé :**
```powershell
python --version
```

Le répertoire `backend-mcp/data/` sera créé automatiquement au premier démarrage du service.

---

### Étape 2 : Lancer les services

**Méthode 1 : Script automatique (Recommandé)**

1. Ouvrir PowerShell dans le dossier du projet :
   ```powershell
   cd C:\Users\YasserAITLAZIZ\sfd-clm
   ```

2. Double-cliquer sur `tests\start_services.bat`
   
   OU exécuter dans PowerShell :
   ```powershell
   .\tests\start_services.bat
   ```

3. Deux nouvelles fenêtres CMD s'ouvriront automatiquement :
   - **Fenêtre 1** : Mock Salesforce (port 8001)
   - **Fenêtre 2** : Backend MCP (port 8000)

4. Attendre que vous voyiez dans chaque fenêtre :
   ```
   INFO:     Uvicorn running on http://0.0.0.0:8001 (Press CTRL+C to quit)
   INFO:     Started reloader process
   INFO:     Started server process
   INFO:     Waiting for application startup.
   INFO:     Application startup complete.
   ```

**Méthode 2 : Démarrage manuel (Pour débogage)**

**Terminal 1 - Mock Salesforce :**
```powershell
cd C:\Users\YasserAITLAZIZ\sfd-clm\mock-salesforce
uvicorn app.main:app --port 8001 --reload
```

**Terminal 2 - Backend MCP :**
```powershell
cd C:\Users\YasserAITLAZIZ\sfd-clm\backend-mcp
uvicorn app.main:app --port 8000 --reload
```

---

### Étape 3 : Vérifier que tout fonctionne

Ouvrir un **nouveau terminal PowerShell** et tester :

```powershell
# Test 1 : Health check Mock Salesforce
curl http://localhost:8001/health

# Test 2 : Health check Backend MCP
curl http://localhost:8000/health
```

**Résultat attendu :**
```json
{
  "status": "healthy",
  "service": "mock-salesforce",
  "version": "1.0.0"
}
```

```json
{
  "status": "healthy",
  "service": "backend-mcp",
  "version": "1.0.0"
}
```

---

## ✅ Vérification Complète

### Test 1 : Accéder aux interfaces Swagger

Ouvrir dans votre navigateur :
- **Mock Salesforce** : http://localhost:8001/docs
- **Backend MCP** : http://localhost:8000/docs

Vous devriez voir l'interface Swagger avec tous les endpoints.

### Test 2 : Test rapide du pipeline

Dans un nouveau terminal :
```powershell
cd C:\Users\YasserAITLAZIZ\sfd-clm
python tests\test_pipeline_simple.py
```

---

## 🛑 Arrêter les services

### Méthode 1 : Fermer les fenêtres
- Fermer les fenêtres CMD où les services tournent
- Appuyer sur `CTRL+C` dans chaque fenêtre

### Méthode 2 : Via le gestionnaire de tâches
1. Ouvrir le Gestionnaire des tâches (Ctrl+Shift+Esc)
2. Chercher les processus `python.exe` ou `uvicorn`
3. Cliquer sur "Terminer la tâche"

### Méthode 3 : Via PowerShell
```powershell
# Trouver les processus sur les ports
netstat -ano | findstr :8000
netstat -ano | findstr :8001

# Tuer les processus (remplacer <PID> par le numéro trouvé)
taskkill /PID <PID> /F
```

---

## 🔧 Dépannage Windows

### Erreur : "Erreur de base de données SQLite"
**Solution :**
1. Vérifier que le répertoire `backend-mcp/data/` existe et est accessible en écriture
2. Vérifier le chemin de la base de données dans la configuration (`SESSION_DB_PATH`)
3. Le répertoire `data/` sera créé automatiquement si nécessaire
4. Redémarrer PowerShell

### Erreur : "uvicorn n'est pas reconnu"
**Solution :**
```powershell
# Installer uvicorn
pip install uvicorn[standard]

# Ou installer toutes les dépendances
cd backend-mcp
pip install -r requirements.txt
cd ..\mock-salesforce
pip install -r requirements.txt
```

### Erreur : "Port 8000/8001 déjà utilisé"
**Solution :**
```powershell
# Trouver le processus
netstat -ano | findstr :8000

# Tuer le processus (remplacer <PID>)
taskkill /PID <PID> /F
```

### Erreur : "Module 'app' not found"
**Solution :**
- S'assurer d'être dans le bon dossier
- Vérifier que la structure des dossiers est correcte
- Réinstaller les dépendances

---

## 📋 Checklist de Démarrage

Avant de lancer les tests, vérifier :

- [ ] SQLite est disponible (inclus dans Python, aucune action requise)
- [ ] Les ports 8000 et 8001 sont libres
- [ ] Les dépendances sont installées (`pip install -r requirements.txt`)
- [ ] Les services démarrent sans erreur
- [ ] Les health checks répondent correctement
- [ ] Les interfaces Swagger sont accessibles

---

## 🚀 Une fois tout démarré

Vous pouvez maintenant :

1. **Lancer les tests** :
   ```powershell
   python tests\test_pipeline_simple.py
   ```

2. **Tester manuellement via Swagger** :
   - http://localhost:8001/docs
   - http://localhost:8000/docs

3. **Tester avec curl** :
   ```powershell
   curl -X POST http://localhost:8001/mock/salesforce/get-record-data `
     -H "Content-Type: application/json" `
     -d '{\"record_id\": \"001XXXX\"}'
   ```

---

## 💡 Astuces

- **Garder les fenêtres ouvertes** : Les services doivent rester actifs
- **Mode reload** : Les services redémarrent automatiquement si vous modifiez le code
- **Logs en temps réel** : Regardez les fenêtres CMD pour voir les logs
- **Erreurs** : Les erreurs apparaissent directement dans les fenêtres des services

