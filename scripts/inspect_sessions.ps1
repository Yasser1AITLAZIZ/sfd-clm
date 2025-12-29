# Script PowerShell pour inspecter la base de données sessions.db depuis Windows
# Usage: .\scripts\inspect_sessions.ps1

$ProjectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $ProjectRoot

$ContainerName = "sfd-clm-backend-mcp"

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Inspection de la base de données SQLite" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Vérifier si le conteneur est en cours d'exécution
$containerRunning = docker ps --filter "name=$ContainerName" --format "{{.Names}}"
if (-not $containerRunning) {
    Write-Host "❌ Le conteneur '$ContainerName' n'est pas en cours d'exécution." -ForegroundColor Red
    Write-Host "   Démarrez-le avec: docker-compose up -d" -ForegroundColor Yellow
    exit 1
}

Write-Host "✓ Conteneur trouvé: $ContainerName" -ForegroundColor Green
Write-Host ""

# Copier le script si nécessaire
$scriptPath = Join-Path $ProjectRoot "backend-mcp\scripts\inspect_sessions_db.py"
if (Test-Path $scriptPath) {
    Write-Host "Copie du script d'inspection dans le conteneur..." -ForegroundColor Yellow
    docker cp $scriptPath "${ContainerName}:/app/inspect_sessions_db.py" | Out-Null
    Write-Host "✓ Script copié" -ForegroundColor Green
    Write-Host ""
}

# Exécuter le script d'inspection
Write-Host "Exécution de l'inspection..." -ForegroundColor Yellow
Write-Host ""
docker exec $ContainerName python /app/inspect_sessions_db.py

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Inspection terminée" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Pour voir les logs avec les erreurs détaillées:" -ForegroundColor Yellow
Write-Host "  docker-compose logs backend-mcp --tail=200 | Select-String -Pattern 'ERROR|error|Exception|exception' -Context 5" -ForegroundColor White

