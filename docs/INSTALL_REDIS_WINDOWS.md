# Installation de Redis sur Windows

## Méthode 1 : Installation via WSL (Recommandé - Plus stable)

### Étape 1 : Installer WSL (Windows Subsystem for Linux)

1. **Ouvrir PowerShell en tant qu'Administrateur**
   - Clic droit sur PowerShell → "Exécuter en tant qu'administrateur"

2. **Installer WSL 2**
   ```powershell
   wsl --install
   ```

3. **Redémarrer l'ordinateur** (si demandé)

4. **Après redémarrage, installer Ubuntu**
   ```powershell
   wsl --install -d Ubuntu
   ```

### Étape 2 : Installer Redis dans WSL

1. **Ouvrir Ubuntu** (depuis le menu Démarrer)

2. **Mettre à jour les packages**
   ```bash
   sudo apt update
   sudo apt upgrade -y
   ```

3. **Installer Redis**
   ```bash
   sudo apt install redis-server -y
   ```

4. **Démarrer Redis**
   ```bash
   sudo service redis-server start
   ```

5. **Vérifier que Redis fonctionne**
   ```bash
   redis-cli ping
   ```
   Devrait répondre : `PONG`

6. **Configurer Redis pour démarrer automatiquement**
   ```bash
   sudo systemctl enable redis-server
   ```

### Étape 3 : Accéder à Redis depuis Windows

Redis dans WSL est accessible depuis Windows sur `localhost:6379` par défaut.

**Tester depuis PowerShell Windows :**
```powershell
# Installer redis-cli pour Windows (optionnel)
# Ou utiliser WSL pour les commandes
wsl redis-cli ping
```

---

## Méthode 2 : Installation native Windows (Alternative)

### Option A : Memurai (Redis compatible pour Windows)

1. **Télécharger Memurai**
   - Site : https://www.memurai.com/
   - Version gratuite disponible

2. **Installer Memurai**
   - Exécuter l'installateur
   - Suivre les instructions d'installation
   - Memurai s'installe comme service Windows

3. **Vérifier l'installation**
   ```powershell
   # Memurai inclut redis-cli
   redis-cli ping
   ```

### Option B : Redis via Docker (Si Docker Desktop est installé)

1. **Vérifier que Docker Desktop est installé**
   ```powershell
   docker --version
   ```

2. **Lancer Redis dans un conteneur Docker**
   ```powershell
   docker run -d -p 6379:6379 --name redis redis:latest
   ```

3. **Vérifier que Redis fonctionne**
   ```powershell
   docker exec -it redis redis-cli ping
   ```
   Devrait répondre : `PONG`

4. **Pour démarrer Redis à chaque démarrage de Docker**
   ```powershell
   docker start redis
   ```

### Option C : Redis natif Windows (Ancienne version)

⚠️ **Note :** Cette version n'est plus maintenue officiellement, mais peut fonctionner.

1. **Télécharger Redis pour Windows**
   - Repository : https://github.com/microsoftarchive/redis/releases
   - Télécharger la dernière version (ex: `Redis-x64-3.0.504.zip`)

2. **Extraire l'archive**
   - Extraire dans `C:\Redis` (ou autre dossier)

3. **Ajouter au PATH**
   - Ouvrir "Variables d'environnement" (Win + R → `sysdm.cpl` → Avancé)
   - Ajouter `C:\Redis` au PATH système

4. **Démarrer Redis**
   ```powershell
   cd C:\Redis
   redis-server.exe
   ```

5. **Dans un autre terminal, tester**
   ```powershell
   redis-cli.exe ping
   ```

---

## Méthode 3 : Installation via Chocolatey (Si installé)

Si vous avez Chocolatey installé :

```powershell
# Installer Redis
choco install redis-64 -y

# Démarrer Redis
redis-server
```

---

## Vérification de l'installation

### Test 1 : Vérifier que Redis répond

```powershell
redis-cli ping
```

**Résultat attendu :** `PONG`

### Test 2 : Tester depuis Python

```powershell
python
```

```python
import redis
r = redis.Redis(host='localhost', port=6379, db=0)
r.ping()
```

**Résultat attendu :** `True`

### Test 3 : Tester depuis le projet

```powershell
cd C:\Users\YasserAITLAZIZ\sfd-clm
python check_redis_install.py
```

---

## Configuration pour le projet

Une fois Redis installé, vérifier la configuration dans `backend-mcp/app/core/config.py` :

```python
redis_url: str = "redis://localhost:6379/0"
```

Cette configuration devrait fonctionner par défaut.

---

## Démarrer Redis automatiquement

### Avec WSL
```bash
# Dans Ubuntu WSL
sudo systemctl enable redis-server
```

### Avec Memurai
- Memurai s'installe automatiquement comme service Windows
- Démarre automatiquement au boot

### Avec Docker
Créer un script de démarrage ou utiliser Docker Compose (voir `docker-compose.yml`)

---

## Dépannage

### Erreur : "redis-cli n'est pas reconnu"

**Solution :**
1. Vérifier que Redis est dans le PATH
2. Ou utiliser le chemin complet : `C:\Redis\redis-cli.exe`
3. Ou utiliser WSL : `wsl redis-cli ping`

### Erreur : "Connection refused"

**Solution :**
1. Vérifier que Redis est démarré
2. Vérifier le port (6379 par défaut)
3. Vérifier le firewall Windows

### Erreur : "Port 6379 already in use"

**Solution :**
```powershell
# Trouver le processus
netstat -ano | findstr :6379

# Tuer le processus (remplacer <PID>)
taskkill /PID <PID> /F
```

---

## Recommandation

Pour Windows, je recommande :
1. **WSL 2 + Redis** (le plus stable et proche de Linux)
2. **Docker + Redis** (si Docker Desktop est déjà installé)
3. **Memurai** (solution native Windows, gratuite)

---

## Test rapide après installation

```powershell
# 1. Démarrer Redis (selon votre méthode)
# WSL: wsl sudo service redis-server start
# Docker: docker start redis
# Memurai: Démarre automatiquement

# 2. Tester
redis-cli ping

# 3. Si ça répond PONG, vous êtes prêt !
```

