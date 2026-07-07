@echo off
setlocal

set "ROOT=%~dp0"
cd /d "%ROOT%"

rem Try pythonw first so the launcher stays windowed when available
where pythonw >nul 2>nul
if %errorlevel%==0 (
  start "" pythonw "%ROOT%launch_paper_forensics.pyw"
  exit /b 0
)

rem Fall back to the Windows Python Launcher (.pyw file association)
where pyw >nul 2>nul
if %errorlevel%==0 (
  start "" pyw "%ROOT%launch_paper_forensics.pyw"
  exit /b 0
)

rem Last resort: plain python (will briefly flash a console window)
where py >nul 2>nul
if %errorlevel%==0 (
  start "" py "%ROOT%launch_paper_forensics.pyw"
  exit /b 0
)

where python >nul 2>nul
if %errorlevel%==0 (
  start "" python "%ROOT%launch_paper_forensics.pyw"
  exit /b 0
)

echo paper-forensics could not find pythonw.exe, pyw.exe, py.exe, or python.exe.
echo Please install Python for Windows (python.org) or another supported distribution.
pause
