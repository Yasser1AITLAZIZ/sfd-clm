@echo off
REM Quick test runner for Windows

echo ==========================================
echo OptiClaims Pipeline Tests
echo ==========================================
echo.

REM Check if services are running
echo Checking services...
curl -s http://localhost:8001/health >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Mock Salesforce is not running on port 8001
    echo         Please start it first: tests\start_services.bat
    pause
    exit /b 1
)

curl -s http://localhost:8000/health >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Backend MCP is not running on port 8000
    echo         Please start it first: tests\start_services.bat
    pause
    exit /b 1
)

echo [OK] Both services are running
echo.

REM Run tests
echo Running pipeline tests...
echo.

python tests\test_pipeline_simple.py

echo.
echo Tests completed!
echo Check test_results.json for detailed results
echo.
pause

