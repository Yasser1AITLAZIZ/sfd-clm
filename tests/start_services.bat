@echo off
REM Script to start all services for testing (Windows)

echo ==========================================
echo Starting OptiClaims Services for Testing
echo ==========================================
echo.

REM Check if Redis is running
echo Checking Redis...
redis-cli ping >nul 2>&1
if %errorlevel% equ 0 (
    echo [OK] Redis is running
) else (
    echo [WARNING] Redis is not running. Please start it manually.
    echo           Run: redis-server
    pause
    exit /b 1
)

echo.

REM Start Mock Salesforce service
echo Starting Mock Salesforce service on port 8001...
start "Mock Salesforce" cmd /k "cd mock-salesforce && uvicorn app.main:app --port 8001 --reload"
timeout /t 3 /nobreak >nul

REM Check if Mock Salesforce started
curl -s http://localhost:8001/health >nul 2>&1
if %errorlevel% equ 0 (
    echo [OK] Mock Salesforce service started
) else (
    echo [ERROR] Failed to start Mock Salesforce service
    pause
    exit /b 1
)

echo.

REM Start Backend MCP service
echo Starting Backend MCP service on port 8000...
start "Backend MCP" cmd /k "cd backend-mcp && uvicorn app.main:app --port 8000 --reload"
timeout /t 3 /nobreak >nul

REM Check if Backend MCP started
curl -s http://localhost:8000/health >nul 2>&1
if %errorlevel% equ 0 (
    echo [OK] Backend MCP service started
) else (
    echo [ERROR] Failed to start Backend MCP service
    pause
    exit /b 1
)

echo.
echo ==========================================
echo All services are running!
echo ==========================================
echo.
echo Mock Salesforce: http://localhost:8001
echo Backend MCP: http://localhost:8000
echo.
echo Services are running in separate windows.
echo Close those windows to stop the services.
echo.
echo Ready for testing! Run: python tests\test_pipeline_simple.py
echo.
pause

