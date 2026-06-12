@echo off
chcp 65001 >nul
title DaVinci Resolve 转剪映草稿 - 卸载
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0uninstall.ps1"
echo.
pause
