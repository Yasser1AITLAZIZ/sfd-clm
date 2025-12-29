# Script to stop all test services (Windows)

Write-Host "Stopping test services..." -ForegroundColor Yellow

# Try to kill processes by port
$ports = @(8000, 8001, 8002)
$killed = $false

foreach ($port in $ports) {
    $processes = Get-NetTCPConnection -LocalPort $port -ErrorAction SilentlyContinue | Select-Object -ExpandProperty OwningProcess -Unique
    foreach ($processId in $processes) {
        if ($processId) {
            Write-Host "Killing process on port $port (PID: $processId)" -ForegroundColor Yellow
            Stop-Process -Id $processId -Force -ErrorAction SilentlyContinue
            $killed = $true
        }
    }
}

if ($killed) {
    Write-Host "[OK] Services stopped" -ForegroundColor Green
} else {
    Write-Host "[WARNING] No services found running on ports 8000, 8001, 8002" -ForegroundColor Yellow
}

Write-Host "Done" -ForegroundColor Cyan

