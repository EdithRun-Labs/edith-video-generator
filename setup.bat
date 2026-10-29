@echo off
setlocal enabledelayedexpansion
cd /d "%~dp0"

echo == edith-video-generator setup

set "PY="
where py >nul 2>&1
if %errorlevel%==0 set "PY=py -3"
if not defined PY (
  where python >nul 2>&1
  if !errorlevel!==0 set "PY=python"
)

if not defined PY (
  echo.
  echo !! Python 3 was not found.
  echo    Install Python 3.11 or newer from https://www.python.org/downloads/windows/
  echo    Tick "Add python.exe to PATH" in the installer, then run setup.bat again.
  echo.
  pause
  exit /b 1
)

%PY% -c "import sys; sys.exit(0 if sys.version_info >= (3,11) else 1)"
if errorlevel 1 (
  echo.
  echo !! This needs Python 3.11 or newer. Install a newer one from
  echo    https://www.python.org/downloads/windows/ and run setup.bat again.
  echo.
  pause
  exit /b 1
)

echo == Using %PY%

if not exist ".venv\Scripts\python.exe" (
  echo == Creating .venv
  %PY% -m venv .venv
  if errorlevel 1 (
    echo.
    echo !! Could not create the virtual environment.
    pause
    exit /b 1
  )
)

rem A .venv made by "uv venv" has no pip; add it rather than starting over.
".venv\Scripts\python.exe" -m pip --version >nul 2>&1
if errorlevel 1 (
  echo == Adding pip to .venv
  ".venv\Scripts\python.exe" -m ensurepip --upgrade --default-pip >nul 2>&1
  if errorlevel 1 (
    echo.
    echo !! This .venv has no pip and ensurepip could not add it.
    echo    Delete the .venv folder and run setup.bat again.
    pause
    exit /b 1
  )
)

echo == Installing the tool and its Python packages ^(a minute or two^)
".venv\Scripts\python.exe" -m pip install --upgrade pip --quiet
".venv\Scripts\python.exe" -m pip install --quiet -e ".[dev,tts-onnx]"
if errorlevel 1 (
  echo.
  echo !! The install failed. The message above says why: usually no network,
  echo    or not enough disk space.
  pause
  exit /b 1
)

where node >nul 2>&1
if errorlevel 1 (
  echo.
  echo == Node is not installed, and the renderer needs it.
  where winget >nul 2>&1
  if errorlevel 1 (
    echo    Install Node 20+ from https://nodejs.org/, then run: cd video ^&^& npm install
  ) else (
    choice /c YN /n /m "Install Node 20+ with winget now? [Y/n] "
    if errorlevel 2 (
      echo    Skipped. Later: install Node, then run: cd video ^&^& npm install
    ) else (
      winget install --id OpenJS.NodeJS.LTS -e --accept-package-agreements --accept-source-agreements
      echo    Node installed. If npm is still not found, close and reopen this window.
    )
  )
)

where npm >nul 2>&1
if errorlevel 1 (
  echo.
  echo == The renderer packages are not installed ^(npm not found yet^).
  echo    Reopen the terminal, then run: cd video ^&^& npm install
) else (
  echo == Installing the renderer packages ^(one time, about 100 MB^)
  pushd video
  call npm install --no-audit --no-fund
  if errorlevel 1 (
    echo.
    echo !! npm install failed. The speech commands still work; retry with:
    echo    cd video ^&^& npm install
  )
  popd
)

echo == The speech weights ^(one time, about 340 MB^)
".venv\Scripts\python.exe" -m edith fetch
if errorlevel 1 (
  echo    The weights were not downloaded. Later: .venv\Scripts\python.exe -m edith fetch
)

echo == Checking external tools
".venv\Scripts\python.exe" -m edith doctor

echo.
echo Next steps, one line at a time:
echo.
echo   .venv\Scripts\python.exe -m edith init --out project.yaml
echo   .venv\Scripts\python.exe -m edith build project.yaml
echo   .venv\Scripts\python.exe -m edith render project.yaml
echo.
echo Put your text in sources\. Everything else is written by the wizard.
echo.
pause
endlocal
