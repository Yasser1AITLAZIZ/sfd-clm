# Guide Rapide : Installer Redis sur Windows

## 🚀 Solution la plus rapide : Docker

Si vous avez Docker Desktop installé :

```powershell
# Lancer Redis dans Docker
docker run -d -p 6379:6379 --name redis redis:latest

# Tester
docker exec -it redis redis-cli ping
# Devrait répondre: PONG
```

**Pour démarrer Redis plus tard :**
```powershell
docker start redis
```

---

## 🐧 Solution recommandée : WSL 2

### Étape 1 : Installer WSL 2

1. **Ouvrir PowerShell en tant qu'Administrateur**
   - Win + X → "Windows PowerShell (Admin)"

2. **Installer WSL**
   ```powershell
   wsl --install
   ```

3. **Redémarrer l'ordinateur**

### Étape 2 : Installer Redis dans Ubuntu WSL

1. **Ouvrir Ubuntu** (depuis le menu Démarrer)

2. **Installer Redis**
   ```bash
   sudo apt update
   sudo apt install redis-server -y
   ```

3. **Démarrer Redis**
   ```bash
   sudo service redis-server start
   ```

4. **Tester**
   ```bash
   redis-cli ping
   ```
   Devrait répondre : `PONG`

5. **Configurer pour démarrer automatiquement**
   ```bash
   sudo systemctl enable redis-server
   ```

### Étape 3 : Utiliser depuis Windows

Redis dans WSL est accessible depuis Windows sur `localhost:6379`.

**Tester depuis PowerShell Windows :**
```powershell
# Option 1 : Via WSL
wsl redis-cli ping

# Option 2 : Depuis Python (si redis-py est installé)
python -c "import redis; r = redis.Redis(); print(r.ping())"
```

---

## 🪟 Solution native Windows : Memurai

1. **Télécharger Memurai**
   - Site : https://www.memurai.com/get-memurai
   - Version Developer (gratuite)

2. **Installer Memurai**
   - Exécuter l'installateur
   - Suivre les instructions
   - Memurai s'installe comme service Windows

3. **Tester**
   ```powershell
   redis-cli ping
   ```
   Devrait répondre : `PONG`

---

## ✅ Vérification après installation

### Test 1 : redis-cli
```powershell
redis-cli ping
```
**Résultat attendu :** `PONG`

### Test 2 : Depuis Python
```powershell
python
```
```python
import redis
r = redis.Redis(host='localhost', port=6379, db=0)
print(r.ping())
```
**Résultat attendu :** `True`

### Test 3 : Script du projet
```powershell
cd C:\Users\YasserAITLAZIZ\sfd-clm
python check_redis_install.py
```

---

## 🔧 Dépannage

### "redis-cli n'est pas reconnu"

**Si installé via WSL :**
```powershell
wsl redis-cli ping
```

**Si installé via Docker :**
```powershell
docker exec -it redis redis-cli ping
```

**Si installé via Memurai :**
- Vérifier que Memurai est démarré (Services Windows)
- Ajouter le chemin d'installation au PATH si nécessaire

### "Connection refused"

1. **Vérifier que Redis est démarré**
   - WSL : `wsl sudo service redis-server status`
   - Docker : `docker ps` (doit voir le conteneur redis)
   - Memurai : Vérifier dans Services Windows

2. **Démarrer Redis**
   - WSL : `wsl sudo service redis-server start`
   - Docker : `docker start redis`
   - Memurai : Démarrer le service dans Services Windows

### Port 6379 déjà utilisé

```powershell
# Trouver le processus
netstat -ano | findstr :6379

# Tuer le processus (remplacer <PID>)
taskkill /PID <PID> /F
```

---

## 📋 Checklist

- [ ] Redis installé (WSL/Docker/Memurai)
- [ ] Redis démarré
- [ ] `redis-cli ping` répond `PONG`
- [ ] Test Python fonctionne
- [ ] Configuration dans `backend-mcp/app/core/config.py` correcte

---

## 🎯 Recommandation pour votre cas

Vu que vous êtes sur Windows, je recommande :

1. **Si Docker Desktop est installé** → Utiliser Docker (le plus simple)
2. **Sinon** → Installer WSL 2 + Redis (le plus stable)
3. **Alternative** → Memurai (solution native Windows)

---

## 🚀 Après installation

Une fois Redis installé et fonctionnel :

1. **Démarrer les services**
   ```powershell
   .\tests\start_services.bat
   ```

2. **Lancer les tests**
   ```powershell
   python tests\test_pipeline_simple.py
   ```

