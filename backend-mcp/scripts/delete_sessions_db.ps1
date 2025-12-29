# Script simple pour supprimer sessions.db
# Usage: .\delete_sessions_db.ps1

$dbPath = "data\sessions.db"

Write-Host "Suppression de $dbPath..." -ForegroundColor Yellow

if (Test-Path $dbPath) {
    try {
        Remove-Item $dbPath -Force
        Write-Host "✓ Fichier supprimé avec succès!" -ForegroundColor Green
        Write-Host "La nouvelle structure sera créée automatiquement au prochain démarrage." -ForegroundColor Green
    } catch {
        Write-Host "✗ Erreur: $_" -ForegroundColor Red
        Write-Host ""
        Write-Host "Le fichier est verrouillé. Veuillez:" -ForegroundColor Yellow
        Write-Host "1. Arrêter tous les serveurs (uvicorn, fastapi)" -ForegroundColor White
        Write-Host "2. Fermer DB Browser ou autres outils de base de données" -ForegroundColor White
        Write-Host "3. Redémarrer votre IDE si nécessaire" -ForegroundColor White
    }
} else {
    Write-Host "Le fichier n'existe pas." -ForegroundColor Green
}

