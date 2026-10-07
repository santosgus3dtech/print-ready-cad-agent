@echo off
setlocal
cd /d "%~dp0"
where uv >nul 2>nul
if errorlevel 1 (
  echo uv is required. See README.md.
  pause
  exit /b 1
)
uv sync --locked --python 3.11
if errorlevel 1 goto failed
pushd frontend
call npm ci
if errorlevel 1 goto failed
call npm run build
if errorlevel 1 goto failed
popd
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\start-local.ps1"
exit /b %errorlevel%
:failed
echo Setup failed. Review the messages above.
pause
exit /b 1
