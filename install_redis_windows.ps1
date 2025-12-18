# Script PowerShell pour installer Redis sur Windows
# Options: WSL, Docker, ou Memurai

Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "Installation de Redis pour Windows" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host ""

# Vérifier si Redis est déjà installé
Write-Host "Vérification de Redis..." -ForegroundColor Yellow
try {
    $result = redis-cli ping 2>$null
    if ($result -eq "PONG") {
        Write-Host "✅ Redis est déjà installé et fonctionne!" -ForegroundColor Green
        exit 0
    }
} catch {
    Write-Host "Redis n'est pas installé ou ne fonctionne pas." -ForegroundColor Yellow
}

Write-Host ""
Write-Host "Options d'installation:" -ForegroundColor Cyan
Write-Host "1. WSL 2 + Redis (Recommandé - Plus stable)"
Write-Host "2. Docker + Redis (Si Docker Desktop est installé)"
Write-Host "3. Memurai (Solution native Windows)"
Write-Host "4. Installation manuelle (Guide)"
Write-Host ""

$choice = Read-Host "Choisissez une option (1-4)"

switch ($choice) {
    "1" {
        Write-Host ""
        Write-Host "Installation via WSL 2..." -ForegroundColor Yellow
        Write-Host ""
        Write-Host "Étapes:" -ForegroundColor Cyan
        Write-Host "1. Installer WSL 2 (PowerShell Admin requis)"
        Write-Host "2. Installer Ubuntu dans WSL"
        Write-Host "3. Installer Redis dans Ubuntu"
        Write-Host ""
        Write-Host "Commandes à exécuter:" -ForegroundColor Yellow
        Write-Host "  # Dans PowerShell Admin:"
        Write-Host "  wsl --install"
        Write-Host ""
        Write-Host "  # Après redémarrage, dans Ubuntu WSL:"
        Write-Host "  sudo apt update"
        Write-Host "  sudo apt install redis-server -y"
        Write-Host "  sudo service redis-server start"
        Write-Host ""
        Write-Host "  # Tester:"
        Write-Host "  wsl redis-cli ping"
        Write-Host ""
        Write-Host "Voir docs/INSTALL_REDIS_WINDOWS.md pour plus de détails" -ForegroundColor Green
    }
    "2" {
        Write-Host ""
        Write-Host "Installation via Docker..." -ForegroundColor Yellow
        
        # Vérifier si Docker est installé
        try {
            docker --version | Out-Null
            Write-Host "✅ Docker est installé" -ForegroundColor Green
            Write-Host ""
            Write-Host "Lancement de Redis dans Docker..." -ForegroundColor Yellow
            
            # Lancer Redis
            docker run -d -p 6379:6379 --name redis redis:latest
            
            if ($LASTEXITCODE -eq 0) {
                Write-Host "✅ Redis lancé dans Docker!" -ForegroundColor Green
                Write-Host ""
                Write-Host "Tester avec:" -ForegroundColor Cyan
                Write-Host "  docker exec -it redis redis-cli ping"
            } else {
                Write-Host "❌ Erreur lors du lancement de Redis" -ForegroundColor Red
            }
        } catch {
            Write-Host "❌ Docker n'est pas installé" -ForegroundColor Red
            Write-Host "Installez Docker Desktop depuis: https://www.docker.com/products/docker-desktop" -ForegroundColor Yellow
        }
    }
    "3" {
        Write-Host ""
        Write-Host "Installation via Memurai..." -ForegroundColor Yellow
        Write-Host ""
        Write-Host "1. Télécharger Memurai depuis: https://www.memurai.com/" -ForegroundColor Cyan
        Write-Host "2. Installer Memurai (version gratuite disponible)"
        Write-Host "3. Memurai s'installe comme service Windows"
        Write-Host "4. Tester avec: redis-cli ping"
        Write-Host ""
        Write-Host "Voir docs/INSTALL_REDIS_WINDOWS.md pour plus de détails" -ForegroundColor Green
    }
    "4" {
        Write-Host ""
        Write-Host "Installation manuelle..." -ForegroundColor Yellow
        Write-Host ""
        Write-Host "Voir le guide complet dans: docs/INSTALL_REDIS_WINDOWS.md" -ForegroundColor Cyan
        Write-Host ""
        Write-Host "Options:" -ForegroundColor Yellow
        Write-Host "  - WSL 2 + Redis (Recommandé)"
        Write-Host "  - Docker + Redis"
        Write-Host "  - Memurai (Windows natif)"
        Write-Host "  - Redis Windows (ancienne version)"
    }
    default {
        Write-Host "❌ Option invalide" -ForegroundColor Red
    }
}

Write-Host ""
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "Après installation, tester avec:" -ForegroundColor Yellow
Write-Host "  redis-cli ping" -ForegroundColor White
Write-Host "  (Devrait répondre: PONG)" -ForegroundColor White
Write-Host "==========================================" -ForegroundColor Cyan

