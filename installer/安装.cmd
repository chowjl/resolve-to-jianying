@echo off
chcp 65001 >nul
title DaVinci Resolve 转剪映草稿 - 安装
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0install.ps1"
echo.
pause
