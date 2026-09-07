@echo off
setlocal EnableExtensions EnableDelayedExpansion

if defined HUAWEICLOUD_SKILL_PYTHON (
  "%HUAWEICLOUD_SKILL_PYTHON%" "%~dp0hcloud-skill" %*
  exit /b !ERRORLEVEL!
)

where py >nul 2>nul
if not errorlevel 1 (
  py -3.12 "%~dp0hcloud-skill" %*
  exit /b !ERRORLEVEL!
)

where python >nul 2>nul
if not errorlevel 1 (
  python "%~dp0hcloud-skill" %*
  exit /b !ERRORLEVEL!
)

echo hcloud-skill: Python is unavailable; install Python 3.12+ or set HUAWEICLOUD_SKILL_PYTHON. 1>&2
exit /b 127
