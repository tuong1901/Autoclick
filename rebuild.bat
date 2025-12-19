@echo off
echo ==========================================
echo Rebuilding CTAutoClick Pro EXE
echo ==========================================
echo.

REM Delete old EXE first
echo [1/3] Removing old EXE...
del /F /Q "dist\CTAutoClickPro.exe" 2>nul
timeout /t 1 /nobreak >nul

REM Run build
echo [2/3] Building new EXE...
python build_exe.py

REM Check result
echo.
echo [3/3] Checking result...
if exist "dist\CTAutoClickPro.exe" (
    echo.
    echo ==========================================
    echo BUILD SUCCESS!
    echo ==========================================
    echo Location: dist\CTAutoClickPro.exe
    echo.
) else (
    echo.
    echo ==========================================
    echo BUILD FAILED!
    echo ==========================================
    echo Please close any running instances and try again.
    echo.
)

pause
